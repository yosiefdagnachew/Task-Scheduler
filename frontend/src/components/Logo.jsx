import React from 'react';

export default function Logo({ className = "h-12 w-auto" }) {
  return (
    <svg 
      className={className}
      viewBox="0 0 120 60" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Hexagon outline - light blue */}
      <path
        d="M20 15 L35 5 L50 15 L50 35 L35 45 L20 35 Z"
        stroke="#60A5FA"
        strokeWidth="2.5"
        fill="none"
      />
      
      {/* Clock face inside hexagon (upper-left) */}
      <circle
        cx="30"
        cy="22"
        r="6"
        stroke="#60A5FA"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Clock hands pointing to 10 and 2 o'clock */}
      <line
        x1="30"
        y1="22"
        x2="33"
        y2="20"
        stroke="#60A5FA"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <line
        x1="30"
        y1="22"
        x2="32"
        y2="17"
        stroke="#60A5FA"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      
      {/* Gear icon (behind clock, lower-left) */}
      <circle
        cx="28"
        cy="30"
        r="4"
        stroke="#60A5FA"
        strokeWidth="1"
        fill="none"
        opacity="0.7"
      />
      <circle
        cx="28"
        cy="30"
        r="2"
        fill="#60A5FA"
        opacity="0.7"
      />
      {/* Gear teeth */}
      <rect x="28" y="26" width="1" height="2" fill="#60A5FA" opacity="0.7" />
      <rect x="28" y="32" width="1" height="2" fill="#60A5FA" opacity="0.7" />
      <rect x="26" y="30" width="2" height="1" fill="#60A5FA" opacity="0.7" />
      <rect x="30" y="30" width="2" height="1" fill="#60A5FA" opacity="0.7" />
      
      {/* Checkmark with gradient (bottom-right, extending outside hexagon) */}
      <defs>
        <linearGradient id="checkGradient" x1="40" y1="25" x2="55" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#60A5FA"/>
          <stop offset="100%" stopColor="#2563EB"/>
        </linearGradient>
      </defs>
      <path
        d="M42 28 L48 34 L55 27"
        stroke="url(#checkGradient)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M52 27 L55 30 L58 27"
        stroke="url(#checkGradient)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      
      {/* Text "ISS-TS" below logo */}
      <text
        x="60"
        y="45"
        fontFamily="Arial, sans-serif"
        fontSize="16"
        fontWeight="bold"
        fill="#60A5FA"
        letterSpacing="2"
        textTransform="uppercase"
      >
        ISS-TS
      </text>
    </svg>
  );
}
