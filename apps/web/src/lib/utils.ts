import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const VIEW_SJP = {
  longitude: -49.3804,
  latitude: -20.8196,
  zoom: 11.5,
} as const;
