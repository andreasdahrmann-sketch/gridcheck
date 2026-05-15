import type { CSSProperties } from "react";

type PwaIconProps = {
  size: number;
};

const titleStyle: CSSProperties = {
  fontSize: "22%",
  fontWeight: 800,
  letterSpacing: "-0.04em",
  color: "#F8FAFC",
};

const subtitleStyle: CSSProperties = {
  fontSize: "9%",
  fontWeight: 600,
  letterSpacing: "0.18em",
  textTransform: "uppercase",
  color: "#5FD0B8",
};

export function PwaIcon({ size }: PwaIconProps) {
  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
          "radial-gradient(circle at 20% 10%, rgba(95,208,184,0.22), transparent 36%), radial-gradient(circle at 80% 0%, rgba(238,127,45,0.2), transparent 30%), linear-gradient(180deg, #061A1A 0%, #0A2323 100%)",
        borderRadius: size * 0.22,
        border: `${Math.max(6, size * 0.02)}px solid rgba(255,255,255,0.08)`,
        color: "#E7F3F0",
      }}
    >
      <div
        style={{
          width: "72%",
          height: "72%",
          borderRadius: size * 0.18,
          border: `${Math.max(4, size * 0.016)}px solid rgba(95,208,184,0.32)`,
          background: "rgba(255,255,255,0.05)",
          boxShadow: "0 18px 60px rgba(0,0,0,0.28)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: "16%",
            borderRadius: size * 0.16,
            border: `${Math.max(3, size * 0.012)}px dashed rgba(95,208,184,0.42)`,
          }}
        />
        <div
          style={{
            position: "absolute",
            width: "42%",
            height: "42%",
            borderRadius: "999px",
            border: `${Math.max(4, size * 0.016)}px solid #EE7F2D`,
            boxShadow: "0 0 0 14px rgba(238,127,45,0.12)",
          }}
        />
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: size * 0.025,
            zIndex: 1,
          }}
        >
          <div style={titleStyle}>GC</div>
          <div style={subtitleStyle}>Field</div>
        </div>
      </div>
    </div>
  );
}
