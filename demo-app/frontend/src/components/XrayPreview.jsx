import { useState } from 'react';

export function XrayPreview({ imageUrl, bodyPart, diagnosis, title, className = '' }) {
  const [broken, setBroken] = useState(false);
  const shouldRenderImage = Boolean(imageUrl) && !broken;

  if (shouldRenderImage) {
    return (
      <img
        className={`xray-image ${className}`.trim()}
        src={imageUrl}
        alt={title || 'X-ray image'}
        loading="lazy"
        onError={() => setBroken(true)}
      />
    );
  }

  return (
    <div className={`xray-tile ${className}`.trim()}>
      <span>{bodyPart}</span>
      <strong>{diagnosis}</strong>
    </div>
  );
}
