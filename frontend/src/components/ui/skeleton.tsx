import { cn } from '@/lib/utils';

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-md bg-gradient-to-r from-[oklch(0.91_0.012_75)] via-[oklch(0.95_0.008_75)] to-[oklch(0.91_0.012_75)] bg-[length:200%_100%] animate-[shimmer_1.8s_ease-in-out_infinite]',
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
