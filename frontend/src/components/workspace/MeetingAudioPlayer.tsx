import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
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
import type { ApiTranscriptSegment } from '../../types';
import { nextSpeechPosition, pacingRate, speechIntervals } from '../../utils/speechPlayback';

interface MeetingAudioPlayerProps {
  audioUrl: string;
  getToken: () => Promise<string | null>;
  fallbackDuration?: number | null;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onSeek: (seconds: number) => void;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  segments?: ApiTranscriptSegment[];
}

const PLAYBACK_RATES = [0.75, 1.0, 1.25, 1.5, 2.0];

export const MeetingAudioPlayer: React.FC<MeetingAudioPlayerProps> = ({
  audioUrl,
  getToken,
  fallbackDuration = 0,
  currentTime,
  onTimeUpdate,
  onSeek,
  audioRef,
  segments = [],
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(fallbackDuration || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const [skipSilence, setSkipSilence] = useState(false);
  const [adaptiveSpeed, setAdaptiveSpeed] = useState(false);
  const intervals = useMemo(() => speechIntervals(segments, duration), [segments, duration]);
  const initialPosition = useRef(currentTime);
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  // The meeting audio endpoint requires the Clerk bearer token, which a native
  // <audio src> request cannot send. Fetch once and let the browser play the blob.
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setPlaybackUrl(null);
    setIsPlaying(false);
    setIsLoading(true);
    setHasError(false);
    setAudioError(null);
    setSkipSilence(false);
    setAdaptiveSpeed(false);

    const loadAudio = async () => {
      const token = await getTokenRef.current();
      if (!token) throw new Error('Your session has expired. Refresh the page and sign in again.');
      const response = await fetch(audioUrl, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Could not load this recording. Refresh the page and try again.');
      const blob = await response.blob();
      if (!blob.size) throw new Error('This recording is empty.');
      objectUrl = URL.createObjectURL(blob);
      if (controller.signal.aborted) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      } else {
        setPlaybackUrl(objectUrl);
      }
    };

    loadAudio().catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setIsLoading(false);
      setHasError(true);
      setAudioError(error instanceof Error ? error.message : 'Could not load this recording.');
    });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [audioUrl]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = adaptiveSpeed ? pacingRate(currentTime, segments, playbackRate) : playbackRate;
    if (skipSilence && isPlaying && !audio.seeking) {
      const target = nextSpeechPosition(audio.currentTime, intervals);
      if (target !== null && (!Number.isFinite(audio.duration) || target < audio.duration)) {
        audio.currentTime = target;
        onTimeUpdate(target);
      }
    }
  }, [adaptiveSpeed, skipSilence, isPlaying, currentTime, segments, playbackRate, intervals, audioRef, onTimeUpdate]);

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
      if (initialPosition.current > 0) { audio.currentTime = initialPosition.current; initialPosition.current = 0; }
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
      setAudioError('The browser could not play this recording.');
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
    if (!audio || !playbackUrl) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch((err) => {
        console.warn('Audio play request interrupted:', err);
      });
    }
  }, [isPlaying, audioRef, playbackUrl]);

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
    <div className="p-4 sm:p-5 rounded-xl bg-surface border border-line shadow-sm space-y-3">
      {/* Hidden Native Audio Element */}
      <audio
        ref={audioRef as React.LegacyRef<HTMLAudioElement>}
        src={playbackUrl || undefined}
        preload="auto"
      />

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left Side: Playback Controls & Time */}
        <div className="flex items-center gap-3.5 w-full sm:w-auto">
          {/* Skip Back 5s */}
          <button
            onClick={() => skipSeconds(-5)}
            title="Rewind 5 seconds"
            className="p-2 rounded-xl text-muted hover:text-ink hover:bg-surface transition-colors cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Play / Pause Toggle */}
          <button
            onClick={togglePlay}
            disabled={hasError || isLoading}
            className="w-11 h-11 rounded-full bg-brand hover:bg-brand disabled:opacity-40 text-on-brand flex items-center justify-center cursor-pointer shadow-sm  transition-transform active:scale-95 shrink-0"
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
            className="p-2 rounded-xl text-muted hover:text-ink hover:bg-surface transition-colors cursor-pointer"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          {/* Time & State Labels */}
          <div className="space-y-0.5 min-w-[120px]">
            <div className="text-sm font-bold text-ink flex items-center gap-1.5">
              <span>Meeting Audio</span>
              {isPlaying && (
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              )}
            </div>
            <div className="text-sm font-mono font-bold text-ink">
              {formatTimeSeconds(currentTime)} / {formatTimeSeconds(effectiveDuration)}
            </div>
          </div>
        </div>

        {/* Middle: Progress Scrubber Bar */}
        <div className="flex-1 w-full flex items-center gap-3">
          <div className="relative w-full flex items-center">
            {/* Background Track */}
            <div className="absolute left-0 right-0 h-2 bg-surface rounded-full border border-line overflow-hidden">
              {/* Progress Fill */}
              <div
                className="h-full bg-brand-soft rounded-full transition-all duration-75"
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
              className="px-2.5 py-1.5 rounded-lg bg-surface hover:bg-line text-ink hover:text-ink border border-line text-sm font-mono font-bold transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>{playbackRate}x</span>
            </button>

            {showSpeedMenu && (
              <div className="absolute right-0 bottom-full mb-2 w-24 bg-surface border border-line rounded-xl shadow-sm p-1 z-50 animate-fadeIn">
                {PLAYBACK_RATES.map((rate) => (
                  <button
                    key={rate}
                    onClick={() => handleRateChange(rate)}
                    className={`w-full text-left px-2.5 py-1 text-sm font-mono rounded-lg transition-colors cursor-pointer ${
                      playbackRate === rate
                        ? 'bg-brand text-on-brand font-bold'
                        : 'text-ink hover:bg-line hover:text-ink'
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
              className="p-1.5 rounded-lg text-muted hover:text-ink transition-colors cursor-pointer"
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-700" />
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
              className="w-16 accent-brand h-1.5 bg-surface rounded-lg cursor-pointer hidden md:inline-block"
              aria-label="Volume slider"
            />
          </div>
        </div>
      </div>
      {audioError && <p role="alert" className="text-sm text-rose-700">{audioError}</p>}
      {!!segments.length && <div className="flex flex-wrap gap-4 text-sm text-muted">
        <label className="flex items-center gap-2 cursor-pointer" title="Uses saved speech timestamps with padding. Untranscribed sound may be skipped; turn off to hear the original recording."><input type="checkbox" checked={skipSilence} onChange={e => setSkipSilence(e.target.checked)} className="accent-violet-500" />Skip silence (transcript gaps)</label>
        <label className="flex items-center gap-2 cursor-pointer" title="Adjusts your selected speed using approximate words per minute; turn off to keep a fixed speed."><input type="checkbox" checked={adaptiveSpeed} onChange={e => setAdaptiveSpeed(e.target.checked)} className="accent-violet-500" />Adaptive speed</label>
      </div>}
    </div>
  );
};
