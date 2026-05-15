import { ImageResponse } from "next/og";
import { PwaIcon } from "../pwa-icon";

export const runtime = "edge";

export function GET() {
  return new ImageResponse(<PwaIcon size={192} />, {
    width: 192,
    height: 192,
  });
}
