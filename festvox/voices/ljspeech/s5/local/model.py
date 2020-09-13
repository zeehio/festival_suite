import os, sys

FALCON_DIR = os.environ.get('FALCONDIR')
sys.path.append(FALCON_DIR)
from models import *

class Decoder_TacotronOneSeqwise(Decoder_TacotronOne):
    def __init__(self, in_dim, r):
        super(Decoder_TacotronOneSeqwise, self).__init__(in_dim, r)
        self.prenet = Prenet_seqwise(in_dim * r, sizes=[256, 128])


class TacotronOneSeqwise(TacotronOne):

    def __init__(self, n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, padding_idx=None, use_memory_mask=False):
        super(TacotronOneSeqwise, self).__init__(n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, padding_idx=None, use_memory_mask=False)
        self.decoder = Decoder_TacotronOneSeqwise(mel_dim, r)

class TacotronOneSeqwiseqF0s(TacotronOneSeqwise):

    def __init__(self, n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, num_qF0s=20, padding_idx=None, use_memory_mask=False):
        super(TacotronOneSeqwiseqF0s, self).__init__(n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, padding_idx=None, use_memory_mask=False)

        self.qF0_embedding = nn.Embedding(num_qF0s, 128)
        self.embeddings2inputs = SequenceWise(nn.Linear(embedding_dim + 128, embedding_dim))


    def forward(self, inputs, qF0s, targets=None, input_lengths=None):

        B = inputs.size(0)

        # Embeddings for Text
        inputs = self.embedding(inputs)

        # Embeddings for quantized F0s
        qF0s_embedding = self.qF0_embedding(qF0s)

        # Combination
        inputs = torch.cat([inputs, qF0s_embedding], dim=-1)
        inputs = self.embeddings2inputs(inputs) 

        # Text Encoder
        encoded_phonemes = self.encoder(inputs, input_lengths)
        decoder_inputs = encoded_phonemes

        # Decoder
        mel_outputs, alignments = self.decoder(decoder_inputs, targets, memory_lengths=input_lengths)
        mel_outputs = mel_outputs.view(B, -1, self.mel_dim)

        # PostNet
        linear_outputs = self.postnet(mel_outputs)
        linear_outputs = self.last_linear(linear_outputs)

        return mel_outputs, linear_outputs, alignments

class TacotronOneSeqwiseStress(TacotronOneSeqwise):

    def __init__(self, n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, num_qF0s=2, padding_idx=None, use_memory_mask=False):
        super(TacotronOneSeqwiseStress, self).__init__(n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, padding_idx=None, use_memory_mask=False)

        self.qF0_embedding = nn.Embedding(num_qF0s, 32)
        self.embeddings2inputs = SequenceWise(nn.Linear(embedding_dim + 32, embedding_dim))


    def forward(self, inputs, qF0s, targets=None, input_lengths=None):

        B = inputs.size(0)

        # Embeddings for Text
        inputs = self.embedding(inputs)

        # Embeddings for quantized F0s
        qF0s_embedding = self.qF0_embedding(qF0s)

        # Combination
        inputs = torch.cat([inputs, qF0s_embedding], dim=-1)
        inputs = torch.tanh(self.embeddings2inputs(inputs))

        # Text Encoder
        encoded_phonemes = self.encoder(inputs, input_lengths)
        decoder_inputs = encoded_phonemes

        # Decoder
        mel_outputs, alignments = self.decoder(decoder_inputs, targets, memory_lengths=input_lengths)
        mel_outputs = mel_outputs.view(B, -1, self.mel_dim)

        # PostNet
        linear_outputs = self.postnet(mel_outputs)
        linear_outputs = self.last_linear(linear_outputs)

        return mel_outputs, linear_outputs, alignments



class DownsamplingEncoder(nn.Module):
    """
        Input: (N, samples_i) numeric tensor
        Output: (N, samples_o, channels) numeric tensor
    """
    def __init__(self, channels, layer_specs):
        super().__init__()

        self.convs_wide = nn.ModuleList()
        self.convs_1x1 = nn.ModuleList()
        self.layer_specs = layer_specs
        prev_channels = 80
        total_scale = 1
        pad_left = 0
        self.skips = []
        for stride, ksz, dilation_factor in layer_specs:
            conv_wide = nn.Conv1d(prev_channels, 2 * channels, ksz, stride=stride, dilation=dilation_factor)
            wsize = 2.967 / math.sqrt(ksz * prev_channels)
            conv_wide.weight.data.uniform_(-wsize, wsize)
            conv_wide.bias.data.zero_()
            self.convs_wide.append(conv_wide)

            conv_1x1 = nn.Conv1d(channels, channels, 1)
            conv_1x1.bias.data.zero_()
            self.convs_1x1.append(conv_1x1)

            prev_channels = channels
            skip = (ksz - stride) * dilation_factor
            pad_left += total_scale * skip
            self.skips.append(skip)
            total_scale *= stride
        self.pad_left = pad_left
        self.total_scale = total_scale

        self.final_conv_0 = nn.Conv1d(channels, channels, 1)
        self.final_conv_0.bias.data.zero_()
        self.final_conv_1 = nn.Conv1d(channels, channels, 1)

    def forward(self, samples):
        x = samples.transpose(1,2) #.unsqueeze(1)
        #print("Shape of input: ", x.shape)
        for i, stuff in enumerate(zip(self.convs_wide, self.convs_1x1, self.layer_specs, self.skips)):
            conv_wide, conv_1x1, layer_spec, skip = stuff
            stride, ksz, dilation_factor = layer_spec
            #print(i)
            x1 = conv_wide(x)
            x1_a, x1_b = x1.split(x1.size(1) // 2, dim=1)
            x2 = torch.tanh(x1_a) * torch.sigmoid(x1_b)
            x3 = conv_1x1(x2)
            if i == 0:
                x = x3
            else:
                x = x3 + x[:, :, skip:skip+x3.size(2)*stride].view(x.size(0), x3.size(1), x3.size(2), -1)[:, :, :, -1]
        x = self.final_conv_1(F.relu(self.final_conv_0(x)))
        return x.transpose(1, 2)



class TacotronOneGST(TacotronOneSeqwise):

    def __init__(self, n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, num_qF0s=20, padding_idx=None, use_memory_mask=False):
        super(TacotronOneGST, self).__init__(n_vocab, embedding_dim=256, mel_dim=80, linear_dim=1025,
                 r=5, padding_idx=None, use_memory_mask=False)

        encoder_layers = [
            (2, 4, 1),
            (2, 4, 1),
            (2, 4, 1),
            (1, 4, 1),
            (2, 4, 1),
            (1, 4, 1),
            (2, 4, 1),
            (1, 4, 1),
            ]
        self.mel_encoder = DownsamplingEncoder(80, encoder_layers)
        self.mel_lstm = nn.LSTM(80, 128, bidirectional=True, batch_first=True)
        self.mel_linear = SequenceWise(nn.Linear(256, 80))

        self.num_styletokens = 10
        self.attention_layer = SequenceWise(nn.Linear(80, 1))
        self.style_embedding = nn.Parameter(torch.randn(mel_dim, self.num_styletokens))

        self.styleattentionNencodedphonemes2decoderinputs = SequenceWise(nn.Linear(mel_dim + embedding_dim, embedding_dim))


    def forward_gst(self, inputs, targets=None, input_lengths=None):

        B = inputs.size(0)

        # Embeddings for Text
        inputs = self.embedding(inputs)

        # Embeddings for mels
        reference_embedding = self.mel_encoder(targets)
        reference_embedding, _ = self.mel_lstm(reference_embedding)
        reference_embedding = torch.tanh(self.mel_linear(reference_embedding))

        # Attention
        query = reference_embedding[:,-1,:]
        style_embedding_modified = self.style_embedding.expand(B, 80, self.num_styletokens).transpose(1,2)
        #print("Shape of style embedding modified and query: ", style_embedding_modified.shape, query.shape)
        alignment = self.attention_layer(torch.tanh(style_embedding_modified + query.unsqueeze(1)))
        alignment = F.softmax(alignment, dim=1).squeeze(2)
        #print("Shape of alignment: ", alignment.shape, alignment[0,:])
        attention = torch.bmm(alignment.unsqueeze(1), style_embedding_modified).squeeze(1)
        attention = attention.unsqueeze(1).expand(B, inputs.shape[1], 80)
        #print("Shape of attention: ", attention.shape)

        # Text Encoder
        encoded_phonemes = self.encoder(inputs)
        
        # Decoder inputs
        #print("Shape of style_embedding and encoded phonemes: ", attention.shape, encoded_phonemes.shape)
        encoded_phonesNstyle_embedding = torch.cat([encoded_phonemes, attention], dim=-1)
        decoder_inputs = torch.tanh(self.styleattentionNencodedphonemes2decoderinputs(encoded_phonesNstyle_embedding))

        # Decoder
        mel_outputs, alignments = self.decoder(decoder_inputs, targets, memory_lengths=input_lengths)
        mel_outputs = mel_outputs.view(B, -1, self.mel_dim)

        # PostNet
        linear_outputs = self.postnet(mel_outputs)
        linear_outputs = self.last_linear(linear_outputs)

        return mel_outputs, linear_outputs, alignments


    def forward_generate_gst(self, inputs, targets=None, input_lengths=None):

        B = inputs.size(0)

        # Embeddings for Text
        inputs = self.embedding(inputs)

        # Embeddings for mels
        reference_embedding = self.mel_encoder(targets)
        reference_embedding, _ = self.mel_lstm(reference_embedding)
        reference_embedding = torch.tanh(self.mel_linear(reference_embedding))

        # Attention
        query = reference_embedding[:,-1,:]
        style_embedding_modified = self.style_embedding.expand(B, 80, self.num_styletokens).transpose(1,2)
        #print("Shape of style embedding modified and query: ", style_embedding_modified.shape, query.shape)
        alignment = self.attention_layer(torch.tanh(style_embedding_modified + query.unsqueeze(1)))
        alignment = F.softmax(alignment, dim=1).squeeze(2)
        alignment = torch.Tensor([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]).cuda()
        print("Shape of alignment: ", alignment.shape, alignment)
        attention = torch.bmm(alignment.unsqueeze(1), style_embedding_modified).squeeze(1)
        attention = attention.unsqueeze(1).expand(B, inputs.shape[1], 80)
        #print("Shape of attention: ", attention.shape)

        # Text Encoder
        encoded_phonemes = self.encoder(inputs)
        
        # Decoder inputs
        #print("Shape of style_embedding and encoded phonemes: ", attention.shape, encoded_phonemes.shape)
        encoded_phonesNstyle_embedding = torch.cat([encoded_phonemes, attention], dim=-1)
        decoder_inputs = self.styleattentionNencodedphonemes2decoderinputs(encoded_phonesNstyle_embedding)

        targets = None 

        # Decoder
        mel_outputs, alignments = self.decoder(decoder_inputs, targets, memory_lengths=input_lengths)
        mel_outputs = mel_outputs.view(B, -1, self.mel_dim)

        # PostNet
        linear_outputs = self.postnet(mel_outputs)
        linear_outputs = self.last_linear(linear_outputs)

        return mel_outputs, linear_outputs, alignments

