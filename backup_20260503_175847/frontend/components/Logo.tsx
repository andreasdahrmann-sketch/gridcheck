export function Logo({ size = 32 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
        <path d="M20 6 A14 14 0 1 0 32 28 L20 28 L20 22 L26 22"
          stroke="#E67A2E" strokeWidth="4" strokeLinecap="round" fill="none"/>
        <path d="M30 14 A10 10 0 1 0 30 30"
          stroke="#C9D67A" strokeWidth="4" strokeLinecap="round" fill="none"/>
      </svg>
      <span className="font-bold text-white text-lg tracking-tight">GridCheck</span>
    </div>
  )
}
