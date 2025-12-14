export function positionTooltip(
  e: React.MouseEvent<HTMLElement>,
  text: string
): { text: string; x: number; y: number } {
  const padding = 12;
  const estWidth = 260;
  const estHeight = 140;
  let x = e.clientX + padding;
  let y = e.clientY + padding;
  if (x + estWidth > window.innerWidth) {
    x = e.clientX - estWidth - padding;
  }
  if (y + estHeight > window.innerHeight) {
    y = e.clientY - estHeight - padding;
  }
  return { text, x, y };
}

