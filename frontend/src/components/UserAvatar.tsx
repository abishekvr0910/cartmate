import React, { useState } from 'react';

interface UserAvatarProps {
  name: string;
  src?: string | null;
  className?: string;
  imageClassName?: string;
}

export const UserAvatar: React.FC<UserAvatarProps> = ({ name, src, className = '', imageClassName = '' }) => {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || '?';

  return (
    <span
      role="img"
      aria-label={name}
      className={`inline-flex shrink-0 items-center justify-center overflow-hidden bg-gradient-to-br from-emerald-700 to-teal-900 font-bold text-white ${className}`}
    >
      {src && failedSrc !== src ? (
        <img
          src={src}
          alt=""
          className={`h-full w-full object-cover ${imageClassName}`}
          onError={() => setFailedSrc(src)}
        />
      ) : (
        <span aria-hidden="true">{initials}</span>
      )}
    </span>
  );
};
