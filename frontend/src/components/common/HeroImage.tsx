interface HeroImageProps {
  heroId: string;
  heroName: string;
  className?: string;
  style?: React.CSSProperties;
}

export function HeroImage({ heroId, heroName, className = '', style }: HeroImageProps) {
  const src = `./heroes/${heroId}.png`;

  return (
    <img
      src={src}
      alt={heroName}
      className={className}
      style={style}
      onError={e => {
        const target = e.currentTarget;
        target.onerror = null;
        target.style.display = 'none';
        const parent = target.parentElement;
        if (parent) {
          parent.style.background = 'linear-gradient(135deg, #3d2a10, #221910)';
          const initials = document.createElement('span');
          initials.textContent = heroName.slice(0, 2).toUpperCase();
          initials.style.cssText = 'color:#f27f0d;font-weight:900;font-size:1.5rem;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)';
          parent.style.position = 'relative';
          parent.appendChild(initials);
        }
      }}
    />
  );
}
