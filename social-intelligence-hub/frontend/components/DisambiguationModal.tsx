"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { GraduationCap, TrendingUp, X, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type CapexInterpretation = "institution" | "financial" | null;

interface DisambiguationModalProps {
  isOpen: boolean;
  query: string;
  onSelect: (interpretation: CapexInterpretation) => void;
  onClose: () => void;
}

const OPTIONS = [
  {
    id: "institution" as const,
    icon: GraduationCap,
    title: "CAPEX — Institución Educativa",
    subtitle: "Centro de Innovación y Capacitación Profesional",
    description:
      "Buscar menciones, reseñas y publicaciones sobre los cursos, talleres y programas de formación técnica de CAPEX en Santiago, RD.",
    keywords: ["capacitación", "taller", "cursos", "egresados", "Santiago"],
    color: "#1E3A8A",
    bgColor: "#EFF6FF",
    borderColor: "#BFDBFE",
  },
  {
    id: "financial" as const,
    icon: TrendingUp,
    title: "CAPEX — Término Financiero",
    subtitle: "Capital Expenditure / Gastos de Capital",
    description:
      "Buscar análisis sobre gastos de capital, inversiones en activos fijos, reportes financieros y métricas contables.",
    keywords: ["inversión", "activos fijos", "balance", "finanzas"],
    color: "#92400E",
    bgColor: "#FFFBEB",
    borderColor: "#FDE68A",
  },
];

export function DisambiguationModal({
  isOpen,
  query,
  onSelect,
  onClose,
}: DisambiguationModalProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen || !mounted) return null;

  return createPortal(
    <>

      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          zIndex: 9998,
        }}
        onClick={onClose}
      />


      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 9999,
          width: "min(520px, calc(100vw - 32px))",
          maxHeight: "calc(100vh - 64px)",
          overflowY: "auto",
        }}
      >
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200">

          <div className="flex items-start gap-3 p-6 pb-4 border-b border-gray-100">
            <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 flex-shrink-0">
              <HelpCircle className="h-5 w-5 text-amber-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-base font-semibold text-gray-900">
                Desambiguación del término{" "}
                <span className="text-blue-700 font-bold">"{query}"</span>
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                El término es ambiguo. Selecciona la interpretación correcta
                para obtener resultados precisos.
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded flex-shrink-0"
            >
              <X className="h-4 w-4" />
            </button>
          </div>


          <div className="p-6 space-y-3">
            {OPTIONS.map((option) => {
              const Icon = option.icon;
              const isHovered = hovered === option.id;

              return (
                <button
                  key={option.id}
                  className="w-full text-left rounded-xl border-2 p-4 transition-all duration-150 hover:shadow-md hover:-translate-y-0.5"
                  style={{
                    backgroundColor: isHovered ? option.bgColor : "white",
                    borderColor: isHovered ? option.color : option.borderColor,
                  }}
                  onMouseEnter={() => setHovered(option.id)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelect(option.id)}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="p-2 rounded-lg flex-shrink-0 mt-0.5"
                      style={{ backgroundColor: `${option.color}15` }}
                    >
                      <Icon className="h-5 w-5" style={{ color: option.color }} />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-sm" style={{ color: option.color }}>
                        {option.title}
                      </p>
                      <p className="text-xs text-gray-500 font-medium mb-1">
                        {option.subtitle}
                      </p>
                      <p className="text-xs text-gray-600 leading-relaxed">
                        {option.description}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {option.keywords.map((kw) => (
                          <span
                            key={kw}
                            className="text-xs px-1.5 py-0.5 rounded font-medium"
                            style={{
                              backgroundColor: `${option.color}12`,
                              color: option.color,
                            }}
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                    <span
                      className="text-lg transition-transform duration-150 mt-1 flex-shrink-0"
                      style={{
                        color: option.color,
                        transform: isHovered ? "translateX(4px)" : "none",
                      }}
                    >
                      →
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="px-6 pb-5">
            <p className="text-xs text-center text-gray-400">
              La selección filtrará los resultados usando palabras clave de
              contexto para eliminar la ambigüedad semántica.
            </p>
          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
