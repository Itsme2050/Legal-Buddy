"use client";

import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { EntityType } from "@/types/research";
import { cn } from "@/lib/utils";

export const ENTITY_STYLES: Record<
  EntityType,
  { dot: string; ring: string; label: string }
> = {
  LAW: { dot: "bg-indigo-600", ring: "border-indigo-300", label: "Law" },
  PROVISION: { dot: "bg-indigo-400", ring: "border-indigo-200", label: "Provision" },
  CASE: { dot: "bg-navy-700", ring: "border-navy-400", label: "Case" },
  COURT: { dot: "bg-navy-900", ring: "border-navy-500", label: "Court" },
  AUTHORITY: { dot: "bg-teal-600", ring: "border-teal-300", label: "Authority" },
  PARTY: { dot: "bg-sky-500", ring: "border-sky-300", label: "Party" },
  PERSON: { dot: "bg-sky-400", ring: "border-sky-200", label: "Person" },
  LOCATION: { dot: "bg-emerald-500", ring: "border-emerald-300", label: "Location" },
  LEGAL_CONCEPT: { dot: "bg-amber-500", ring: "border-amber-300", label: "Concept" },
  DATE: { dot: "bg-rose-400", ring: "border-rose-200", label: "Date" },
};

export type EntityNodeType = Node<
  {
    label: string;
    entityType: EntityType;
    description?: string | null;
    confidence?: number | null;
    dimmed?: boolean;
  },
  "entity"
>;

export const EntityNode = memo(function EntityNode({ data, selected }: NodeProps<EntityNodeType>) {
  const style = ENTITY_STYLES[data.entityType] ?? ENTITY_STYLES.LEGAL_CONCEPT;
  return (
    <div
      data-testid="graph-node"
      className={cn(
        "rounded-lg border-2 bg-white px-3 py-2 text-left shadow-sm transition-all",
        style.ring,
        selected ? "ring-2 ring-teal-400" : "",
        data.dimmed ? "opacity-30" : "opacity-100"
      )}
      style={{ minWidth: 140, maxWidth: 230 }}
    >
      <Handle type="target" position={Position.Top} className="!bg-navy-300" />
      <div className="flex items-center gap-1.5">
        <span className={cn("h-2 w-2 shrink-0 rounded-full", style.dot)} />
        <span className="text-[10px] uppercase tracking-wide text-navy-400">
          {style.label}
        </span>
        {typeof data.confidence === "number" && (
          <span className="ml-auto text-[10px] text-navy-300">
            {Math.round(data.confidence * 100)}%
          </span>
        )}
      </div>
      <div className="mt-0.5 break-words text-xs font-semibold leading-snug text-navy-900">
        {data.label}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-navy-300" />
    </div>
  );
});