import React from 'react';

interface LogoProps {
  className?: string;
  iconOnly?: boolean;
}

export const MeetPilotLogo: React.FC<LogoProps> = ({ className = 'h-8', iconOnly = false }) => {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* Logo Icon SVG */}
      <svg
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-full w-auto filter drop-shadow-[0_2px_8px_rgba(30,64,175,0.3)] hover:scale-105 transition-transform duration-300"
      >
        <defs>
          {/* Gradients matching the beautiful blue/cyan theme */}
          <linearGradient id="micGradient" x1="40" y1="40" x2="160" y2="160" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38BDF8" /> {/* Cyan/sky */}
            <stop offset="50%" stopColor="#2563EB" /> {/* Royal Blue */}
            <stop offset="100%" stopColor="#1E3A8A" /> {/* Dark Blue */}
          </linearGradient>
          <linearGradient id="soundGradient" x1="120" y1="30" x2="180" y2="90" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38BDF8" />
            <stop offset="100%" stopColor="#2563EB" />
          </linearGradient>
          <linearGradient id="trailGradient" x1="30" y1="130" x2="110" y2="110" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2563EB" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* --- SOUND WAVES (Top Right) --- */}
        <path
          d="M 140 60 A 45 45 0 0 1 175 95"
          stroke="url(#soundGradient)"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d="M 148 48 A 60 60 0 0 1 190 90"
          stroke="url(#soundGradient)"
          strokeWidth="6"
          strokeLinecap="round"
          opacity="0.75"
        />
        <path
          d="M 156 36 A 75 75 0 0 1 200 85"
          stroke="url(#soundGradient)"
          strokeWidth="6"
          strokeLinecap="round"
          opacity="0.4"
        />

        {/* --- MICROPHONE BASE & STAND --- */}
        {/* U-Shaped Stand */}
        <path
          d="M 55 95 C 55 135, 125 135, 125 95"
          stroke="url(#micGradient)"
          strokeWidth="10"
          strokeLinecap="round"
          fill="none"
        />
        {/* Vertical Stem */}
        <path
          d="M 90 128 L 90 155"
          stroke="url(#micGradient)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Base Plate */}
        <path
          d="M 70 155 L 110 155"
          stroke="url(#micGradient)"
          strokeWidth="10"
          strokeLinecap="round"
        />

        {/* --- MICROPHONE BODY (Capsule) --- */}
        <rect
          x="65"
          y="40"
          width="50"
          height="75"
          rx="25"
          fill="url(#micGradient)"
        />

        {/* Grill Slots (Left Side) */}
        <rect x="73" y="55" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="73" y="65" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="73" y="75" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="73" y="85" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />

        {/* Grill Slots (Right Side) */}
        <rect x="99" y="55" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="99" y="65" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="99" y="75" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />
        <rect x="99" y="85" width="8" height="4" rx="2" fill="#09090B" opacity="0.3" />

        {/* Center Divider Line */}
        <line x1="90" y1="40" x2="90" y2="115" stroke="#09090B" strokeWidth="2" opacity="0.1" />

        {/* --- JET FLIGHT TRAIL --- */}
        {/* Swooping orbit line around/behind the plane */}
        <path
          d="M 30 135 C 25 90, 80 110, 110 110"
          stroke="url(#trailGradient)"
          strokeWidth="8"
          strokeLinecap="round"
          fill="none"
        />

        {/* --- AIRPLANE (Sleek White Jet) --- */}
        <g transform="translate(10, -5)">
          {/* Main Fuselage */}
          <path
            d="M 65 125 C 80 115, 110 100, 125 95 C 130 93, 133 94, 131 98 C 122 108, 105 125, 95 133 C 90 137, 85 137, 75 135 Z"
            fill="#FFFFFF"
          />
          {/* Big Wings (Main wing facing forward/upwards) */}
          <path
            d="M 98 108 L 75 92 C 73 90, 75 88, 79 90 L 108 102 Z"
            fill="#FFFFFF"
          />
          {/* Tail Wing */}
          <path
            d="M 75 133 L 64 138 C 61 139, 62 135, 65 133 L 73 128 Z"
            fill="#FFFFFF"
          />
          {/* Secondary Wing (lower/behind) */}
          <path
            d="M 98 122 L 95 137 C 94 139, 97 139, 99 137 L 108 120 Z"
            fill="#E2E8F0"
          />
        </g>
      </svg>

      {/* Brand Text */}
      {!iconOnly && (
        <div className="flex flex-col justify-center">
          <div className="flex items-center gap-1.5 leading-none">
            <span className="font-extrabold text-xl tracking-tight text-white">
              MeetPilot
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded-md bg-[#2563EB]/15 text-[#38BDF8] border border-[#2563EB]/30 font-bold uppercase tracking-wider">
              AI
            </span>
          </div>
          <span className="text-[7.5px] font-bold text-[#38BDF8] tracking-[0.22em] uppercase leading-none mt-1 whitespace-nowrap">
            Meeting Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
