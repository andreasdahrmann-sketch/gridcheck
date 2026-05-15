import { ImageResponse } from "next/og";
import { PwaIcon } from "./pwa-icon";

export const runtime = "edge";

export const size = {
  width: 180,
  height: 180,
};

export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(<PwaIcon size={size.width} />, size);
}
