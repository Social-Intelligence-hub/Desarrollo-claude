"use client";

import { cn, getNetSentimentColor, getNetSentimentLabel } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: number;
  icon?: React.ReactNode;
  accentColor?: string;
  loading?: boolean;
  active?: boolean;        // resaltado cuando este KPI está aplicado como filtro
  onClick?: () => void;
  className?: string;
}

export function KpiCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  accentColor = "#1E3A8A",
  loading = false,
  active = false,
  onClick,
  className,
}: KpiCardProps) {
  if (loading) {
    return (
      <div className={cn("bg-card rounded-xl p-5 border shadow-sm", className)}>
        <div className="flex items-start justify-between mb-3">
          <div className="skeleton h-4 w-28 rounded" />
          <div className="skeleton h-8 w-8 rounded-lg" />
        </div>
        <div className="skeleton h-9 w-20 rounded mb-2" />
        <div className="skeleton h-3 w-24 rounded" />
      </div>
    );
  }

  const TrendIcon =
    trend === undefined || trend === 0 ? Minus :
    trend > 0 ? TrendingUp : TrendingDown;

  const trendColor =
    trend === undefined || trend === 0 ? "text-muted-foreground" :
    trend > 0 ? "text-sentiment-positive" : "text-sentiment-negative";

  return (
    <div
      className={cn(
        "bg-white rounded-xl p-5 border border-slate-200 shadow-sm transition-all duration-200",
        onClick && "cursor-pointer hover:shadow-md hover:border-czfs-blue hover:-translate-y-0.5 select-none",
        active && "ring-2 ring-czfs-blue shadow-md -translate-y-0.5 border-czfs-blue",
        className
      )}
      style={{
        borderTopWidth: 4,
        borderTopColor: accentColor,
      }}
      onClick={onClick}
      title={onClick ? "Haz clic para filtrar el feed" : undefined}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-sm font-medium text-muted-foreground leading-tight">
          {title}
        </p>
        {icon && (
          <div
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${accentColor}15` }}
          >
            <span style={{ color: accentColor }}>{icon}</span>
          </div>
        )}
      </div>

      <div className="mb-1">
        <span className="text-3xl font-bold text-foreground tabular-nums">
          {value}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {trend !== undefined && (
          <span className={cn("flex items-center gap-0.5 text-xs font-medium", trendColor)}>
            <TrendIcon className="h-3 w-3" />
            {Math.abs(trend)}%
          </span>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>


      {active && onClick && (
        <p className="text-[10px] font-semibold mt-2" style={{ color: accentColor }}>
          Filtro activo — clic para limpiar
        </p>
      )}
    </div>
  );
}

// ============================================================
// Gauge de Sentimiento Neto
// ============================================================
interface NetSentimentCardProps {
  score: number;
  totalMentions: number;
  loading?: boolean;
  onClick?: () => void;
  active?: boolean;
}

export function NetSentimentCard({
  score,
  totalMentions,
  loading,
  onClick,
  active,
}: NetSentimentCardProps) {
  if (loading) {
    return (
      <div className="bg-card rounded-xl p-5 border shadow-sm">
        <div className="skeleton h-4 w-36 rounded mb-4" />
        <div className="skeleton h-16 w-16 rounded-full mx-auto mb-3" />
        <div className="skeleton h-3 w-full rounded" />
      </div>
    );
  }

  const color = getNetSentimentColor(score);
  const label = getNetSentimentLabel(score);

  // Convertir score (−100 a +100) → ángulo del arco (0° a 180°)
  const angle   = ((score + 100) / 200) * 180;
  const rad     = (angle - 90) * (Math.PI / 180);
  const cx = 60, cy = 60, r = 45;
  const needleX = cx + r * Math.cos(rad);
  const needleY = cy + r * Math.sin(rad);

  return (
    <div
      className={cn(
        "bg-white rounded-xl p-5 border border-slate-200 shadow-sm col-span-1 transition-all duration-200",
        onClick && "cursor-pointer hover:shadow-md hover:border-czfs-blue hover:-translate-y-0.5 select-none",
        active && "ring-2 ring-czfs-blue shadow-md -translate-y-0.5 border-czfs-blue"
      )}
      style={{
        borderTopWidth: 4,
        borderTopColor: color,
      }}
      onClick={onClick}
      title={onClick ? "Haz clic para ver detalle" : undefined}
    >
      <p className="text-sm font-medium text-muted-foreground mb-3">
        Sentimiento Neto
      </p>

      <div className="flex items-center justify-center mb-3">
        <svg width="120" height="70" viewBox="0 0 120 70">
          <path
            d="M 10 60 A 50 50 0 0 1 110 60"
            fill="none" stroke="#e5e7eb" strokeWidth="12" strokeLinecap="round"
          />
          <path
            d="M 10 60 A 50 50 0 0 1 110 60"
            fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
            strokeDasharray={`${(angle / 180) * 157} 157`}
            opacity="0.85"
          />
          <line
            x1={cx} y1={cy} x2={needleX} y2={needleY}
            stroke={color} strokeWidth="2.5" strokeLinecap="round"
          />
          <circle cx={cx} cy={cy} r="3" fill={color} />
          <text x="8"  y="70" fontSize="8" fill="#9ca3af">−100</text>
          <text x="98" y="70" fontSize="8" fill="#9ca3af">+100</text>
        </svg>
      </div>

      <div className="text-center">
        <span className="text-3xl font-bold" style={{ color }}>
          {score >= 0 ? "+" : ""}{score}
        </span>
        <span
          className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {label}
        </span>
      </div>

      <p className="text-xs text-center text-muted-foreground mt-1">
        {totalMentions.toLocaleString()} menciones en el período
      </p>
    </div>
  );
}
