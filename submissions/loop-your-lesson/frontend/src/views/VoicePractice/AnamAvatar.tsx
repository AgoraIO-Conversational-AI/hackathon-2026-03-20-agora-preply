/**
 * Avatar component for voice practice.
 *
 * Renders the Anam video avatar when a remote video track is available
 * (streamed through Agora RTC from ConvoAI's native Anam integration).
 * Falls back to an audio-only indicator when no video is present.
 */
import type { IRemoteVideoTrack } from "agora-rtc-sdk-ng";
import { Mic, MicOff, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef } from "react";

interface AnamAvatarProps {
  isConnected: boolean;
  remoteAudioReady: boolean;
  videoTrack: IRemoteVideoTrack | null;
  studentName: string;
  isMuted: boolean;
  onToggleMute: () => void;
}

export function AnamAvatar({
  isConnected,
  remoteAudioReady,
  videoTrack,
  studentName,
  isMuted,
  onToggleMute,
}: AnamAvatarProps) {
  const videoRef = useRef<HTMLDivElement>(null);

  // Play/stop the remote video track in the container div
  useEffect(() => {
    if (videoTrack && videoRef.current) {
      videoTrack.play(videoRef.current);
      return () => {
        videoTrack.stop();
      };
    }
  }, [videoTrack]);

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Avatar visual — video or audio-only fallback */}
      {videoTrack ? (
        <div
          ref={videoRef}
          className="relative h-48 w-48 overflow-hidden rounded-full shadow-lg"
        />
      ) : (
        <div className="relative flex h-48 w-48 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
          {remoteAudioReady && (
            <div className="absolute inset-0 animate-pulse rounded-full bg-indigo-400 opacity-20" />
          )}
          <div className="flex flex-col items-center gap-1 text-white">
            {remoteAudioReady ? (
              <Volume2 size={48} className="animate-bounce" style={{ animationDuration: "2s" }} />
            ) : (
              <VolumeX size={48} className="opacity-50" />
            )}
            <span className="text-sm font-medium">Practice Partner</span>
          </div>
        </div>
      )}

      {/* Status indicators */}
      <div className="flex items-center gap-2 text-sm">
        {isConnected ? (
          <>
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[color:var(--color-text-secondary)]">
              {videoTrack
                ? `Video avatar active — speaking with ${studentName}...`
                : remoteAudioReady
                  ? `Speaking with ${studentName}...`
                  : "Connecting to avatar..."}
            </span>
          </>
        ) : (
          <>
            <span className="h-2 w-2 rounded-full bg-gray-400" />
            <span className="text-[color:var(--color-text-muted)]">
              Not connected
            </span>
          </>
        )}
      </div>

      {/* Audio controls */}
      {isConnected && (
        <button
          onClick={onToggleMute}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
            isMuted
              ? "bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-950 dark:text-red-300"
              : "bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-950 dark:text-green-300"
          }`}
        >
          {isMuted ? (
            <>
              <MicOff size={16} />
              Unmute Mic
            </>
          ) : (
            <>
              <Mic size={16} />
              Mic On
            </>
          )}
        </button>
      )}
    </div>
  );
}
