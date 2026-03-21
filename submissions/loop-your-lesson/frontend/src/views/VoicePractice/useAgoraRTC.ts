/**
 * Agora RTC hook for voice practice.
 *
 * Manages audio + video connection between student's mic and the ConvoAI agent.
 * Full-duplex: student can speak while avatar is speaking.
 * Video: subscribes to remote video track from Anam avatar (UID 200).
 *
 * Based on: docs/tech-guides/02-agora-rtc-rtm.md
 */
import AgoraRTC, {
  type IAgoraRTCClient,
  type IMicrophoneAudioTrack,
  type IRemoteVideoTrack,
} from "agora-rtc-sdk-ng";
import { useCallback, useEffect, useRef, useState } from "react";

interface JoinParams {
  appId: string;
  channel: string;
  token: string;
  uid: number;
}

interface UseAgoraRTCReturn {
  join: (params: JoinParams) => Promise<void>;
  leave: () => Promise<void>;
  toggleMute: () => void;
  isConnected: boolean;
  isMuted: boolean;
  remoteAudioReady: boolean;
  remoteVideoTrack: IRemoteVideoTrack | null;
  error: string | null;
}

export function useAgoraRTC(): UseAgoraRTCReturn {
  const clientRef = useRef<IAgoraRTCClient | null>(null);
  const localTrackRef = useRef<IMicrophoneAudioTrack | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [remoteAudioReady, setRemoteAudioReady] = useState(false);
  const [remoteVideoTrack, setRemoteVideoTrack] = useState<IRemoteVideoTrack | null>(null);
  const [error, setError] = useState<string | null>(null);

  const join = useCallback(async ({ appId, channel, token, uid }: JoinParams) => {
    try {
      setError(null);
      const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
      clientRef.current = client;

      // Listen for agent's audio and avatar's video streams
      client.on("user-published", async (user, mediaType) => {
        console.log(`[RTC] user-published uid=${user.uid} mediaType=${mediaType}`);
        await client.subscribe(user, mediaType);
        if (mediaType === "audio") {
          user.audioTrack?.play();
          setRemoteAudioReady(true);
        }
        if (mediaType === "video") {
          console.log("[RTC] Video track received from avatar!", user.videoTrack);
          setRemoteVideoTrack(user.videoTrack ?? null);
        }
      });

      client.on("user-unpublished", (_user, mediaType) => {
        console.log(`[RTC] user-unpublished mediaType=${mediaType}`);
        if (mediaType === "audio") {
          setRemoteAudioReady(false);
        }
        if (mediaType === "video") {
          setRemoteVideoTrack(null);
        }
      });

      client.on("user-joined", (user) => {
        console.log(`[RTC] user-joined uid=${user.uid}`);
      });

      // Join channel and publish mic
      await client.join(appId, channel, token, uid);
      const localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack({
        AEC: true,   // Acoustic Echo Cancellation — prevents speaker feedback
        ANS: true,   // Automatic Noise Suppression
        AGC: true,   // Automatic Gain Control
      });
      localTrackRef.current = localAudioTrack;
      await client.publish([localAudioTrack]);
      setIsConnected(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to connect";
      setError(message);
      console.error("Agora RTC join error:", err);
    }
  }, []);

  const toggleMute = useCallback(() => {
    const track = localTrackRef.current;
    if (!track) return;
    track.setEnabled(isMuted); // if muted, enable; if enabled, mute
    setIsMuted(!isMuted);
  }, [isMuted]);

  const leave = useCallback(async () => {
    localTrackRef.current?.close();
    localTrackRef.current = null;
    await clientRef.current?.leave();
    clientRef.current = null;
    setIsConnected(false);
    setIsMuted(false);
    setRemoteAudioReady(false);
    setRemoteVideoTrack(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      localTrackRef.current?.close();
      clientRef.current?.leave();
    };
  }, []);

  return {
    join,
    leave,
    toggleMute,
    isConnected,
    isMuted,
    remoteAudioReady,
    remoteVideoTrack,
    error,
  };
}
