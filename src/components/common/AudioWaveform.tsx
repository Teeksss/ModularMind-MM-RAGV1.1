import React, { useEffect, useRef } from 'react';

interface AudioWaveformProps {
  audioUrl: string;
  height?: number;
  width?: string | number;
  barWidth?: number;
  barGap?: number;
  barColor?: string;
  backgroundColor?: string;
}

const AudioWaveform: React.FC<AudioWaveformProps> = ({
  audioUrl,
  height = 80,
  width = '100%',
  barWidth = 2,
  barGap = 1,
  barColor = '#3b82f6',
  backgroundColor = '#f1f5f9'
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    if (!audioUrl) return;
    
    const fetchAudioData = async () => {
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const response = await fetch(audioUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        
        drawWaveform(audioBuffer);
      } catch (error) {
        console.error('Error loading audio for waveform:', error);
      }
    };
    
    fetchAudioData();
  }, [audioUrl]);
  
  const drawWaveform = (audioBuffer: AudioBuffer) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Get audio data
    const channelData = audioBuffer.getChannelData(0); // Use first channel
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Compute number of samples to skip
    const totalBars = Math.floor(canvas.width / (barWidth + barGap));
    const samplesPerBar = Math.floor(channelData.length / totalBars);
    
    // Draw bars
    ctx.fillStyle = barColor;
    
    for (let i = 0; i < totalBars; i++) {
      // Get max amplitude for this segment
      let maxAmplitude = 0;
      const startSample = i * samplesPerBar;
      
      for (let j = 0; j < samplesPerBar && (startSample + j) < channelData.length; j++) {
        const amplitude = Math.abs(channelData[startSample + j]);
        if (amplitude > maxAmplitude) {
          maxAmplitude = amplitude;
        }
      }
      
      // Draw bar
      const x = i * (barWidth + barGap);
      const barHeight = Math.max(1, maxAmplitude * (canvas.height * 0.8));
      const y = (canvas.height - barHeight) / 2;
      
      ctx.fillRect(x, y, barWidth, barHeight);
    }
  };
  
  return (
    <canvas 
      ref={canvasRef} 
      height={height} 
      width={typeof width === 'number' ? width : width} 
      style={{ width: width, height: height }}
      className="rounded-md"
    />
  );
};

export default AudioWaveform;