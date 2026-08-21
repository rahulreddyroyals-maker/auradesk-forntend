import Link from "next/link";
import Image from "next/image";

export function Logo({
  href,
  size = 32,
  showWordmark = true,
  className = "",
}: {
  href: string;
  size?: number;
  showWordmark?: boolean;
  className?: string;
}) {
  return (
    <Link href={href} className={`flex items-center gap-2 ${className}`}>
      <Image
        src="/logo-icon-256.png"
        alt="AuraDesk"
        width={size}
        height={size}
        className="rounded-full"
        priority
      />
      {showWordmark && (
        <span className="text-lg font-semibold tracking-tight">
          Aura<span className="text-aura-gold-500">Desk</span>
        </span>
      )}
    </Link>
  );
}
