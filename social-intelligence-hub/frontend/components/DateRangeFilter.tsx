"use client";

import { useState } from "react";
import { Calendar, ChevronDown, X } from "lucide-react";
import { cn, DATE_PRESETS, type DateRange, type DatePreset, formatShortDate } from "@/lib/utils";

interface DateRangeFilterProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

export function DateRangeFilter({ value, onChange, className }: DateRangeFilterProps) {
  const [showCustom, setShowCustom] = useState(value.preset === "custom");

  const handlePresetClick = (preset: DatePreset) => {
    if (preset === "custom") {
      setShowCustom(true);
      onChange({ preset: "custom", from: value.from, to: value.to });
    } else {
      setShowCustom(false);
      onChange({ preset });
    }
  };

  const handleFromChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ preset: "custom", from: e.target.value, to: value.to });
  };

  const handleToChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ preset: "custom", from: value.from, to: e.target.value });
  };

  const handleClear = () => {
    setShowCustom(false);
    onChange({ preset: "all" });
  };

  const isFiltered = value.preset !== "all";

  // Etiqueta descriptiva del rango activo
  const rangeLabel = (() => {
    if (value.preset === "all") return null;
    if (value.preset === "custom") {
      const from = value.from ? formatShortDate(new Date(value.from).toISOString()) : "";
      const to   = value.to   ? formatShortDate(new Date(value.to).toISOString())   : "hoy";
      if (from) return `${from} — ${to}`;
      return to ? `Hasta ${to}` : null;
    }
    return DATE_PRESETS.find((p) => p.value === value.preset)?.label ?? null;
  })();

  return (
    <div className={cn("flex flex-col gap-2", className)}>


      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          Período:
        </span>

        <div className="flex gap-1 flex-wrap">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.value}
              onClick={() => handlePresetClick(preset.value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded border transition-all duration-100",
                value.preset === preset.value
                  ? "bg-czfs-blue text-white border-czfs-blue shadow-sm"
                  : "bg-white text-muted-foreground border-border hover:border-czfs-blue/50 hover:text-foreground"
              )}
            >
              {preset.label}
            </button>
          ))}


          {isFiltered && (
            <button
              onClick={handleClear}
              className="p-1.5 rounded border border-border text-muted-foreground hover:text-destructive hover:border-destructive/50 transition-colors"
              title="Limpiar filtro de fecha"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>


        {rangeLabel && value.preset !== "custom" && (
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded border">
            {rangeLabel}
          </span>
        )}
      </div>


      {showCustom && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Desde:</span>
          <input
            type="date"
            value={value.from ?? ""}
            onChange={handleFromChange}
            max={value.to ?? new Date().toISOString().substring(0, 10)}
            className="text-xs border rounded-lg px-2.5 py-1.5 bg-white text-foreground
                       focus:outline-none focus:ring-1 focus:ring-czfs-blue/30 focus:border-czfs-blue
                       transition-colors"
          />
          <span className="text-xs text-muted-foreground">Hasta:</span>
          <input
            type="date"
            value={value.to ?? ""}
            onChange={handleToChange}
            min={value.from ?? undefined}
            max={new Date().toISOString().substring(0, 10)}
            className="text-xs border rounded-lg px-2.5 py-1.5 bg-white text-foreground
                       focus:outline-none focus:ring-1 focus:ring-czfs-blue/30 focus:border-czfs-blue
                       transition-colors"
          />
          {value.from && (
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded border">
              {value.from ? formatShortDate(new Date(value.from).toISOString()) : "—"}
              {" — "}
              {value.to ? formatShortDate(new Date(value.to).toISOString()) : "hoy"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
