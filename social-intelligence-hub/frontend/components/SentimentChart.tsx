"use client";

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  BarChart, Bar,
} from "recharts";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { cn } from "@/lib/utils";
import type { DailyTrend, SentimentSummary } from "@/lib/supabase";

const SENTIMENT_COLORS = {
  positive: "#059669",
  negative: "#DC2626",
  neutral:  "#4B5563",
  mixed:    "#7C3AED",
};

const SENTIMENT_LABELS = {
  positive: "Positivo",
  negative: "Negativo",
  neutral:  "Neutro",
  mixed:    "Mixto",
};

// ============================================================
// Gráfico de tendencia temporal (área apilada)
// ============================================================

interface TrendChartProps {
  data: DailyTrend[];
  loading?: boolean;
  entitySlug?: string;
  onBarClick?: (sentiment: string) => void;
}

export function TrendChart({ data, loading, entitySlug, onBarClick }: TrendChartProps) {
  if (loading) {
    return (
      <div className="bg-card rounded-xl border p-5 shadow-sm">
        <div className="skeleton h-4 w-40 rounded mb-6" />
        <div className="skeleton h-48 w-full rounded" />
      </div>
    );
  }

  const filtered = entitySlug ? data.filter((d) => d.entity_slug === entitySlug) : data;

  const dateMap: Record<string, Record<string, number>> = {};
  filtered.forEach((item) => {
    if (!dateMap[item.mention_date]) {
      dateMap[item.mention_date] = { positive: 0, negative: 0, neutral: 0, mixed: 0 };
    }
    dateMap[item.mention_date][item.sentiment_label] =
      (dateMap[item.mention_date][item.sentiment_label] || 0) + item.mention_count;
  });

  const chartData = Object.entries(dateMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, counts]) => ({
      date,
      dateLabel: (() => {
        try { return format(parseISO(date), "dd MMM", { locale: es }); }
        catch { return date; }
      })(),
      ...counts,
    }));

  if (chartData.length === 0) {
    return (
      <div className="bg-card rounded-xl border p-5 shadow-sm">
        <p className="text-sm font-semibold text-foreground mb-4">Tendencia de Menciones</p>
        <div className="h-48 flex items-center justify-center text-muted-foreground text-sm border-2 border-dashed rounded-lg">
          Sin datos para el período seleccionado
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl border p-5 shadow-sm">
      <p className="text-sm font-semibold text-foreground mb-1">Tendencia de Menciones</p>
      <p className="text-xs text-muted-foreground mb-4">
        Evolución diaria · haz clic en la leyenda para filtrar
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData} margin={{ top: 4, right: 12, left: -20, bottom: 0 }}>
          <defs>
            {Object.entries(SENTIMENT_COLORS).map(([key, color]) => (
              <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color} stopOpacity={0.2} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
          <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "white", border: "1px solid #e5e7eb",
              borderRadius: "8px", fontSize: "12px",
            }}
            labelStyle={{ fontWeight: 600, marginBottom: 4 }}
          />
          {Object.entries(SENTIMENT_COLORS).map(([key, color]) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={SENTIMENT_LABELS[key as keyof typeof SENTIMENT_LABELS]}
              stackId="1"
              stroke={color}
              fill={`url(#grad-${key})`}
              strokeWidth={2}
              style={onBarClick ? { cursor: "pointer" } : {}}
              onClick={() => onBarClick?.(key)}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================
// Donut de distribución de sentimiento
// ============================================================

interface SentimentDonutProps {
  summary: SentimentSummary | null;
  loading?: boolean;
  onSliceClick?: (sentiment: string) => void;
}

export function SentimentDonut({ summary, loading, onSliceClick }: SentimentDonutProps) {
  if (loading) {
    return (
      <div className="bg-card rounded-xl border p-5 shadow-sm">
        <div className="skeleton h-4 w-36 rounded mb-6" />
        <div className="skeleton h-36 w-36 rounded-full mx-auto" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-card rounded-xl border p-5 shadow-sm flex items-center justify-center min-h-[200px]">
        <p className="text-muted-foreground text-sm">Sin datos de sentimiento</p>
      </div>
    );
  }

  const pieData = [
    { name: "Positivo", key: "positive", value: summary.positive_count },
    { name: "Negativo", key: "negative", value: summary.negative_count },
    { name: "Neutro",   key: "neutral",  value: summary.neutral_count  },
    { name: "Mixto",    key: "mixed",    value: summary.mixed_count    },
  ]
    .filter((d) => d.value > 0)
    .map((d) => ({ ...d, color: SENTIMENT_COLORS[d.key as keyof typeof SENTIMENT_COLORS] }));

  return (
    <div className="bg-card rounded-xl border p-5 shadow-sm">
      <p className="text-sm font-semibold text-foreground mb-1">
        Distribución de Sentimiento
      </p>
      <p className="text-xs text-muted-foreground mb-3">
        {summary.entity_name}
        {onSliceClick && " · haz clic en un segmento para filtrar"}
      </p>

      <ResponsiveContainer width="100%" height={185}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%" cy="50%"
            innerRadius={48} outerRadius={72}
            paddingAngle={3}
            dataKey="value"
            style={onSliceClick ? { cursor: "pointer" } : {}}
            onClick={(d) => onSliceClick?.(d.key)}
          >
            {pieData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string) => [
              `${value} (${summary.total_mentions > 0
                ? Math.round((value / summary.total_mentions) * 100) : 0}%)`,
              name,
            ]}
            contentStyle={{
              backgroundColor: "white", border: "1px solid #e5e7eb",
              borderRadius: "8px", fontSize: "12px",
            }}
          />
          <Legend
            iconType="circle" iconSize={8}
            formatter={(v) => <span style={{ fontSize: "11px", color: "#6b7280" }}>{v}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

// ============================================================
// Comparativa de entidades (barras horizontales)
// ============================================================

interface EntitiesComparisonChartProps {
  summaries: SentimentSummary[];
  loading?: boolean;
  onEntityClick?: (entitySlug: string) => void;
}

export function EntitiesComparisonChart({
  summaries,
  loading,
  onEntityClick,
}: EntitiesComparisonChartProps) {
  if (loading) {
    return (
      <div className="bg-card rounded-xl border p-5 shadow-sm">
        <div className="skeleton h-4 w-44 rounded mb-6" />
        <div className="skeleton h-32 w-full rounded" />
      </div>
    );
  }

  const chartData = summaries.map((s) => {
    const netScore = s.total_mentions > 0 
      ? Math.round(((s.positive_count - s.negative_count) / s.total_mentions) * 100) 
      : 0;
    
    return {
      name:      s.entity_name.length > 18 ? s.entity_name.substring(0, 16) + "…" : s.entity_name,
      slug:      s.entity_slug,
      fullName:  s.entity_name,
      Positivo:  s.positive_count,
      Negativo:  s.negative_count,
      Neutro:    s.neutral_count,
      netScore:  netScore,
    };
  });

  return (
    <div className="bg-card rounded-xl border p-5 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm font-semibold text-foreground">
          Ranking de Reputación
        </p>
        <span className="text-[10px] font-bold text-muted-foreground uppercase bg-muted px-2 py-0.5 rounded">
          Net Sentiment %
        </span>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Comparativa de salud de marca por entidad
      </p>
      <ResponsiveContainer width="100%" height={Math.max(160, chartData.length * 50)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 0, right: 40, top: 0, bottom: 0 }}
          style={onEntityClick ? { cursor: "pointer" } : {}}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} hide />
          <YAxis
            type="category" dataKey="name"
            tick={{ fontSize: 11, fill: "#6b7280", fontWeight: 500 }} tickLine={false} axisLine={false}
            width={110}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white border p-3 rounded-lg shadow-lg text-xs space-y-1.5">
                    <p className="font-bold border-b pb-1 mb-1">{data.fullName}</p>
                    <div className="flex justify-between gap-4">
                      <span className="text-emerald-600 font-medium">Positivos:</span>
                      <span>{data.Positivo}</span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-red-600 font-medium">Negativos:</span>
                      <span>{data.Negativo}</span>
                    </div>
                    <div className="flex justify-between gap-4 font-bold border-t pt-1 mt-1">
                      <span>Reputación:</span>
                      <span className={data.netScore >= 0 ? "text-emerald-600" : "text-red-600"}>
                        {data.netScore}%
                      </span>
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar dataKey="Positivo" fill={SENTIMENT_COLORS.positive} radius={[0, 0, 0, 0]} stackId="a"
               onClick={(d) => onEntityClick?.(d.slug)} barSize={12} />
          <Bar dataKey="Neutro"   fill={SENTIMENT_COLORS.neutral}  radius={[0, 0, 0, 0]} stackId="a"
               onClick={(d) => onEntityClick?.(d.slug)} barSize={12} />
          <Bar dataKey="Negativo" fill={SENTIMENT_COLORS.negative} radius={[4, 4, 4, 4]} stackId="a"
               onClick={(d) => onEntityClick?.(d.slug)} barSize={12} />
        </BarChart>
      </ResponsiveContainer>

      {/* Mini tabla de ranking rápida */}
      <div className="mt-4 space-y-2">
        {chartData.sort((a, b) => b.netScore - a.netScore).map((item, idx) => (
          <div
            key={item.slug}
            className={cn(
              "flex items-center justify-between text-[11px] p-2.5 rounded-xl border transition-all duration-200",
              "bg-muted/40 border-slate-100 hover:border-slate-200 hover:bg-white hover:shadow-sm"
            )}
          >
            <div className="flex items-center gap-2.5">
              <span className="w-5 h-5 flex items-center justify-center bg-white border shadow-sm rounded-full text-[9px] font-bold text-slate-500">
                {idx + 1}
              </span>
              <span className="font-semibold text-slate-700">{item.fullName}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-end">
                <span className="font-bold text-slate-900">
                  {item.netScore > 0 ? "+" : ""}{item.netScore}%
                </span>
                <span className="text-[9px] text-muted-foreground">
                  {item.Positivo + item.Neutro + item.Negativo} menciones
                </span>
              </div>
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold",
                  item.netScore >= 50 ? "bg-emerald-500" :
                  item.netScore >= 0 ? "bg-blue-500" :
                  item.netScore >= -50 ? "bg-amber-500" :
                  "bg-red-500"
                )}
              >
                {item.netScore >= 0 ? "✓" : "!"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
