# Copyright 2017 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Compute input examples for VGGish from audio waveform."""

import numpy as np
import resampy
from scipy.io import wavfile

import mel_features
import vggish_params
import six


def waveform_to_examples(data, sample_rate): # data:(220500)  samplerate: 44140
  """Converts audio waveform into an array of examples for VGGish.

  Args:
    data: np.array of either one dimension (mono) or two dimensions
      (multi-channel, with the outer dimension representing channels).
      Each sample is generally expected to lie in the range [-1.0, +1.0],
      although this is not required.
    sample_rate: Sample rate of data.

  Returns:
    3-D np.array of shape [num_examples, num_frames, num_bands] which represents
    a sequence of examples, each of which contains a patch of log mel
    spectrogram(梅尔频谱), covering num_frames frames of audio and num_bands mel frequency
    bands, where the frame length is vggish_params.STFT_HOP_LENGTH_SECONDS.
  """
  # Convert to mono. 如果为多声道转为单声道
  if len(data.shape) > 1:
    data = np.mean(data, axis=1)
  # Resample to the rate assumed by VGGish.
  if sample_rate != vggish_params.SAMPLE_RATE:   # 如果传入的采样率和参数文件中定义的不一致则重新进行采样  vggish_params.SAMPLE_RATE=16000
    data = resampy.resample(data, sample_rate, vggish_params.SAMPLE_RATE) #(80000)

  # Compute log mel spectrogram features. 生成梅尔频谱特征，细节再看
  # (498,64)
  log_mel = mel_features.log_mel_spectrogram(
      data,  #(80000)
      audio_sample_rate=vggish_params.SAMPLE_RATE,  #(16000) 
      log_offset=vggish_params.LOG_OFFSET,  #0.01  避免log值陷入负无穷
      window_length_secs=vggish_params.STFT_WINDOW_LENGTH_SECONDS,  #0.025
      hop_length_secs=vggish_params.STFT_HOP_LENGTH_SECONDS,   #0.010 hop:跳跃
      num_mel_bins=vggish_params.NUM_MEL_BINS,  #64
      lower_edge_hertz=vggish_params.MEL_MIN_HZ,  #125
      upper_edge_hertz=vggish_params.MEL_MAX_HZ)  #7500  

  # Frame features into examples.
  features_sample_rate = 1.0 / vggish_params.STFT_HOP_LENGTH_SECONDS  # 1/0.010
  example_window_length = int(round(
      vggish_params.EXAMPLE_WINDOW_SECONDS * features_sample_rate)) # 0.96*100=96
  example_hop_length = int(round(
      vggish_params.EXAMPLE_HOP_SECONDS * features_sample_rate)) # 0.96*100=96
  log_mel_examples = mel_features.frame(
      log_mel,
      window_length=example_window_length,
      hop_length=example_hop_length)
  return log_mel_examples  # (5,96,64)--> [num_examples, num_frames, num_bands]


def wavfile_to_examples(wav_file):
  """Convenience wrapper around waveform_to_examples() for a common WAV format.

  Args:
    wav_file: String path to a file, or a file-like object. The file
    is assumed to contain WAV audio data with signed 16-bit PCM samples.

  Returns:
    See waveform_to_examples.
  """
  # sr为采样率
  sr, wav_data = wavfile.read(wav_file)  # sr:44100  wav_data:(172216,2)
  assert wav_data.dtype == np.int16, 'Bad sample type: %r' % wav_data.dtype
  samples = wav_data / 32768.0  # Convert to [-1.0, +1.0]
  return waveform_to_examples(samples, sr)
