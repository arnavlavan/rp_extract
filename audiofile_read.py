# 2015-04 by Thomas Lidy

# MP3 READ: mini function to decode mp3 using external program
# as there is no Python library for it, we need to use external tools (mpg123, lame, ffmpeg)

import os         # for calling external program for mp3 decoding
import subprocess # for subprocess calls
import tempfile
import uuid

# Reading WAV files
# from scipy.io import wavfile
# scipy.io.wavfile does not support 24 bit Wav files
# therefore we switch to wavio by Warren Weckesser - https://github.com/WarrenWeckesser/wavio - BSD 3-Clause License
import wavio



class DecoderException(Exception):
    
    def __init__(self, message, command=[], orig_error=None):

        # Call the base class constructor with the parameters it needs
        super(DecoderException, self).__init__(message)
        self.command        = command
        self.original_error = orig_error




# Normalize integer WAV data to float in range (-1,1)
# Note that this works fine with Wav files read with Wavio
# when using scipy.io.wavfile to read Wav files, use divisor = np.iinfo(wavedata.dtype).max + 1
# but in this case it will not work with 24 bit files due to scipy scaling 24 bit up to 32bit
def normalize_wav(wavedata,samplewidth):

    # samplewidth in byte (i.e.: 1 = 8bit, 2 = 16bit, 3 = 24bit, 4 = 32bit)
    divisor  = 2**(8*samplewidth)/2
    wavedata = wavedata / float(divisor)
    return (wavedata)



def wav_read(filename,normalize=True,verbose=True,auto_resample=True):
    '''read WAV files

    :param filename: input filename to read from
    :param normalize: normalize the read values (usually signed integers) to range (-1,1)
    :param verbose: output some information during reading
    :param auto_resample: auto-resampling: if sample rate is different than 11, 22 or 44 kHz it will resample to 44 khZ
    :return: tuple of 3 elements: samplereate (e.g. 44100), samplewith (e.g. 2 for 16 bit) and wavedata (simple array for mono, 2-dim. array for stereo)
    '''

    # check if file exists
    if not os.path.exists(filename):
        raise NameError("File does not exist:" + filename)

    samplerate, samplewidth, wavedata = wavio.readwav(filename)

    if auto_resample and samplerate != 11025 and samplerate != 22050 and samplerate != 44100:
        #print original file info
        if verbose: print samplerate, "Hz,", wavedata.shape[1], "channel(s),", wavedata.shape[0], "samples"

        # TODO: if < 44100 and > 22050 downsample to 22050 etc.
        filename2 = resample(filename, to_samplerate=44100, normalize=True, verbose=True)
        samplerate, samplewidth, wavedata = wavio.readwav(filename2)
        os.remove(filename2) # delete temp file

    if (normalize):
        wavedata = normalize_wav(wavedata,samplewidth)

    return (samplerate, samplewidth, wavedata)


def get_temp_filename(suffix=None):
    
    temp_dir      = tempfile.gettempdir()
    rand_filename = str(uuid.uuid4())

    if suffix != None:
        rand_filename = "%s%s" % (rand_filename, suffix)
        
    return os.path.join(temp_dir, rand_filename)


def resample(filename, to_samplerate=44100, normalize=True, verbose=True):

    tempfile = get_temp_filename(suffix='.wav')

    try:
        cmd = ['ffmpeg','-v','1','-y','-i', filename, '-ar', str(to_samplerate), tempfile]

        return_code = subprocess.call(cmd)  # subprocess.call takes a list of command + arguments

        if return_code != 0:
            raise DecoderException("Problem appeared during resampling.", command=cmd)
        if (verbose): print 'Resampled with:', " ".join(cmd)

    except OSError as e:
        if e.errno != 2: #  2 = No such file or directory (i.e. decoder not found, which we want to catch at the end below)
            if os.path.exists(tempfile):
                os.remove(tempfile)
            raise DecoderException("Problem appeared during resampling.", cmd=cmd, orig_error=e)

    return tempfile


# mp3_decode:
# calls external MP3 decoder to convert an mp3 file to a wav file
# mpg123, ffmpeg or lame must be installed on the system (consider adding their path  using os.environ['PATH'] += os.pathsep + path )
# if out_filename is omitted, the input filename is used, replacing the extension by .wav

def mp3_decode(in_filename, out_filename=None, verbose=True):

    basename, ext = os.path.splitext(in_filename)
    ext = ext.lower()

    if out_filename == None:
        out_filename = basename + '.wav'

    # check a number of external MP3 decoder tools whether they are available on the system

    # for subprocess.call, we prepare the commands and the arguments as a list
    # cmd_list is a list of commands with their arguments, which will be iterated over to try to find each tool
    # cmd_types is a list of file types supported by each command/tool

    cmd1 = ['ffmpeg','-v','1','-y','-i', in_filename,  out_filename]    # -v adjusts log level, -y option overwrites output file, because it has been created already by tempfile above
    cmd1_types = ('.mp3','.aif','.aiff','.m4a')
    cmd2 = ['mpg123','-q', '-w', out_filename, in_filename]
    cmd2_types = '.mp3'
    cmd3 = ['lame','--quiet','--decode', in_filename, out_filename]
    cmd3_types = '.mp3'

    cmd_list = [cmd1,cmd2,cmd3]
    cmd_types = [cmd1_types,cmd2_types,cmd3_types]

    success = False

    for cmd, types in zip(cmd_list,cmd_types):

        if ext in types: # only if the current command supports the file type that we are having
            try:
                return_code = subprocess.call(cmd)  # subprocess.call takes a list of command + arguments

                if return_code != 0: raise DecoderException("Problem appeared during decoding.", command=cmd)
                if verbose: print 'Decoded', ext, 'with:', " ".join(cmd)
                success = True

            except OSError as e:
                if e.errno != 2: #  2 = No such file or directory (i.e. decoder not found, which we want to catch at the end below)
                    raise DecoderException("Problem appeared during decoding.", cmd=cmd, orig_error=e)

        if success:
            break  # no need to loop further

    if not success:
        commands = ", ".join( c[0] for c in cmd_list)
        raise OSError("No appropriate decoder found for" + ext + "file. Check if any of these programs is on your system path: " + commands + \
                       ". Otherwise install one of these and/or add them to the path using os.environ['PATH'] += os.pathsep + path.")


# mp3_read:
# call mp3_decode and read from wav file ,then delete wav file
# returns samplereate (e.g. 44100), samplewith (e.g. 2 for 16 bit) and wavedata (simple array for mono, 2-dim. array for stereo)

def mp3_read(filename,normalize=True,verbose=True):

    tempfile = get_temp_filename(suffix='.wav')

    try:
        mp3_decode(filename,tempfile,verbose)
        samplerate, samplewidth, wavedata = wav_read(tempfile,normalize,verbose)

    finally: # delete temp file

        if os.path.exists(tempfile):
            os.remove(tempfile)

    return (samplerate, samplewidth, wavedata)


def aif_read(filename,normalize=True,verbose=True):

    tempfile = get_temp_filename(suffix='.wav')

    try:
        cmd = ['ffmpeg','-v','1','-y','-i', filename,  tempfile]

        return_code = subprocess.call(cmd)  # subprocess.call takes a list of command + arguments

        if return_code != 0:
            raise DecoderException("Problem appeared during decoding.", command=cmd)
        if (verbose): print 'Decoded AIFF file with:', " ".join(cmd)

        samplerate, samplewidth, wavedata = wav_read(tempfile,normalize,verbose)

    except OSError as e:
        if e.errno != 2: #  2 = No such file or directory (i.e. decoder not found, which we want to catch at the end below)
            raise DecoderException("Problem appeared during decoding.", cmd=cmd, orig_error=e)

    finally: # delete temp file

        if os.path.exists(tempfile):
            os.remove(tempfile)

    return (samplerate, samplewidth, wavedata)


def audiofile_read(filename,normalize=True,verbose=True):
    ''' audiofile_read

    generic function capable of reading WAV, MP3 and AIF(F) files

    :param filename: file name path to audio file
    :param normalize: normalize to (-1,1) if True (default), or keep original values (16 bit, 24 bit or 32 bit)
    :param verbose: whether to print a message while decoding files or not
    :return: a tuple with 3 entries: samplerate in Hz (e.g. 44100), samplewidth in bytes (e.g. 2 for 16 bit) and wavedata (simple array for mono, 2-dim. array for stereo)

    Example:
    >>> samplerate, samplewidth, wavedata = audiofile_read("music/BoxCat_Games_-_10_-_Epic_Song.mp3",verbose=False)
    >>> print samplerate, "Hz,", samplewidth*8, "bit,", wavedata.shape[1], "channels,", wavedata.shape[0], "samples"
    44100 Hz, 16 bit, 2 channels, 2421504 samples

    '''

    # check if file exists
    if not os.path.exists(filename):
        raise NameError("File does not exist:" + filename)

    basename, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == '.wav':
        return(wav_read(filename,normalize,verbose))
    else:
        try: # try to decode
            tempfile = get_temp_filename(suffix='.wav')
            mp3_decode(filename,tempfile,verbose)
            samplerate, samplewidth, wavedata = wav_read(tempfile,normalize,verbose)

        finally: # delete temp file in any case
            if os.path.exists(tempfile):
                os.remove(tempfile)
    return (samplerate, samplewidth, wavedata)


# function to self test audiofile_read if working properly
def self_test():
    import doctest
    #doctest.testmod()
    doctest.run_docstring_examples(audiofile_read, globals())


# main routine: to test if decoding works properly

if __name__ == '__main__':

    # to run self test:
    #self_test()
    #exit()
    # (no output means that everything went fine)

    import sys

    # if your MP3 decoder is not on the system PATH, add it like this:
    # path = '/path/to/ffmpeg/'
    # os.environ['PATH'] += os.pathsep + path
    
    # test audio file: "Epic Song" by "BoxCat Game" (included in repository)
    # Epic Song by BoxCat Games is licensed under a Creative Commons Attribution License.
    # http://freemusicarchive.org/music/BoxCat_Games/Nameless_the_Hackers_RPG_Soundtrack/BoxCat_Games_-_Nameless-_the_Hackers_RPG_Soundtrack_-_10_Epic_Song
    if len(sys.argv) > 1:
        file = sys.argv[1]
    else:
        file = "music/BoxCat_Games_-_10_-_Epic_Song.mp3"

    samplerate, samplewidth, wavedata = audiofile_read(file)

    print "Successfully read audio file:"
    print samplerate, "Hz,", samplewidth*8, "bit,", wavedata.shape[1], "channels,", wavedata.shape[0], "samples"
