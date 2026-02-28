import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const USD_TO_PLN = 3.57;

export function formatPLN(usd: number): string {
  return `${(usd * USD_TO_PLN).toFixed(2)} PLN`;
}
