import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  RotateCcw,
  RotateCw,
  Loader2,
  Sliders,
} from 'lucide-react';
import { formatTimeSeconds } from '../../utils/speakerUtils';

interface MeetingAudioPlayerProps {
  audioUrl: string;
  fallbackDuration?: number | null;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onSeek: (seconds: number) => void;
  audioRef: React.RefObject<HTMLAudioElement | null>;
}

const PLAYBACK_RATES = [0.75, 1.0, 1.25, 1.5, 2.0];

export const MeetingAudioPlayer: React.FC<MeetingAudioPlayerProps> = ({
  audioUrl,
  fallbackDuration = 0,
  currentTime,
  onTimeUpdate,
  onSeek,
  audioRef,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(fallbackDuration || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);

  // Sync fallbackDuration if duration not yet loaded from media
  useEffect(() => {
    if (fallbackDuration && fallbackDuration > 0 && duration === 0) {
      setDuration(fallbackDuration);
    }
  }, [fallbackDuration, duration]);

  // Read metadata and attach robust media listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    setIsLoading(true);
    setHasError(false);

    const updateDuration = () => {
      if (audio.duration && !isNaN(audio.duration) && isFinite(audio.duration)) {
        setDuration(audio.duration);
        setIsLoading(false);
      }
    };

    const handleTimeUpdate = () => {
      onTimeUpdate(audio.currentTime);
      updateDuration();
    };

    const handleLoadedMetadata = () => {
      updateDuration();
      setIsLoading(false);
    };

    const handleCanPlay = () => {
      updateDuration();
      setIsLoading(false);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => {
      setIsPlaying(false);
      onTimeUpdate(0);
    };
    const handleError = () => {
      setIsLoading(false);
      setHasError(true);
    };

    // If audio is already loaded/cached in browser, extract immediately
    if (audio.readyState >= 1) {
      updateDuration();
      setIsLoading(false);
    }

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('durationchange', updateDuration);
    audio.addEventListener('loadeddata', updateDuration);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('durationchange', updateDuration);
      audio.removeEventListener('loadeddata', updateDuration);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [audioUrl, audioRef, onTimeUpdate]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch((err) => {
        console.warn('Audio play request interrupted:', err);
      });
    }
  }, [isPlaying, audioRef]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    onSeek(val);
  };

  const skipSeconds = (delta: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const maxDur = duration || fallbackDuration || 100;
    const target = Math.max(0, Math.min(maxDur, audio.currentTime + delta));
    onSeek(target);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audio) {
      audio.volume = val;
      if (val === 0) {
        audio.muted = true;
        setIsMuted(true);
      } else if (isMuted) {
        audio.muted = false;
        setIsMuted(false);
      }
    }
  };

  const handleRateChange = (rate: number) => {
    const audio = audioRef.current;
    setPlaybackRate(rate);
    if (audio) {
      audio.playbackRate = rate;
    }
    setShowSpeedMenu(false);
  };

  const effectiveDuration = duration > 0 ? duration : (fallbackDuration || 0);
  const progressPercent = effectiveDuration > 0 ? Math.min(100, (currentTime / effectiveDuration) * 100) : 0;

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-[#111113] border border-[#27272A] shadow-xl space-y-3">
      {/* Hidden Native Audio Element */}
      <audio
        ref={audioRef as React.LegacyRef<HTMLAudioElement>}
        src={audioUrl}
        preload="auto"
      />

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Side: Playback Controls & Time */}
        <div className="flex items-center gap-3.5 w-full sm:w-auto">
          {/* Skip Back 5s */}
          <button
            onClick={() => skipSeconds(-5)}
            title="Rewind 5 seconds"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Play / Pause Toggle */}
          <button
            onClick={togglePlay}
            disabled={hasError}
            className="w-11 h-11 rounded-full bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-40 text-white flex items-center justify-center cursor-pointer shadow-lg shadow-[#8B5CF6]/30 transition-transform active:scale-95 shrink-0"
          >
            {isLoading && !isPlaying ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isPlaying ? (
              <Pause className="w-5 h-5 fill-current" />
            ) : (
              <Play className="w-5 h-5 fill-current ml-0.5" />
            )}
          </button>

          {/* Skip Forward 5s */}
          <button
            onClick={() => skipSeconds(5)}
            title="Forward 5 seconds"
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-[#18181b] transition-colors cursor-pointer"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          {/* Time & State Labels */}
          <div className="space-y-0.5 min-w-[120px]">
            <div className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>Meeting Audio</span>
              {isPlaying && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </div>
            <div className="text-xs font-mono font-bold text-slate-300">
              {formatTimeSeconds(currentTime)} / {formatTimeSeconds(effectiveDuration)}
            </div>
          </div>
        </div>

        {/* Middle: Progress Scrubber Bar */}
        <div className="flex-1 w-full flex items-center gap-3">
          <div className="relative w-full flex items-center">
            {/* Background Track */}
            <div className="absolute left-0 right-0 h-2 bg-[#18181b] rounded-full border border-[#27272A] overflow-hidden">
              {/* Progress Fill */}
              <div
                className="h-full bg-gradient-to-r from-[#8B5CF6] to-indigo-500 rounded-full transition-all duration-75"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Range Input on Top */}
            <input
              type="range"
              min={0}
              max={effectiveDuration || 100}
              step={0.1}
              value={currentTime}
              onChange={handleSliderChange}
              className="relative w-full h-4 opacity-0 cursor-pointer z-10"
              aria-label="Audio scrubber"
            />
          </div>
        </div>

        {/* Right Side: Speed Selector + Volume Slider */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Speed Selector */}
          <div className="relative">
            <button
              onClick={() => setShowSpeedMenu(!showSpeedMenu)}
              className="px-2.5 py-1.5 rounded-lg bg-[#18181b] hover:bg-[#27272A] text-slate-300 hover:text-white border border-[#27272A] text-xs font-mono font-bold transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>{playbackRate}x</span>
            </button>

            {showSpeedMenu && (
              <div className="absolute right-0 bottom-full mb-2 w-24 bg-[#18181b] border border-[#27272A] rounded-xl shadow-2xl p-1 z-50 animate-fadeIn">
                {PLAYBACK_RATES.map((rate) => (
                  <button
                    key={rate}
                    onClick={() => handleRateChange(rate)}
                    className={`w-full text-left px-2.5 py-1 text-xs font-mono rounded-lg transition-colors cursor-pointer ${
                      playbackRate === rate
                        ? 'bg-[#8B5CF6] text-white font-bold'
                        : 'text-slate-300 hover:bg-[#27272A] hover:text-white'
                    }`}
                  >
                    {rate}x
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Volume Control */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-400" />
              ) : (
                <Volume2 className="w-4 h-4" />
              )}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-16 accent-[#8B5CF6] h-1.5 bg-[#18181b] rounded-lg cursor-pointer hidden md:inline-block"
              aria-label="Volume slider"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
