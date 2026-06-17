"use client";

import React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export type EvidencePageInfo = {
  limit: number;
  offset: number;
  has_more: boolean;
  next_offset: number | null;
};

export type EvidenceSnippet = {
  kind: string;
  text: string;
  truncated?: boolean;
};

export type EvidenceRow = {
  id: string;
  primary: string;
  secondary: string;
  status: string;
  correlationId?: string | null;
  fields: Record<string, React.ReactNode>;
  snippets?: EvidenceSnippet[];
};

type EvidenceTableProps = {
  title: string;
  description: string;
  rows: EvidenceRow[];
  page?: EvidencePageInfo;
  emptyTitle: string;
  loading?: boolean;
  desktopMinWidth?: number;
  importantFields?: string[];
  onSelectRow?: (row: EvidenceRow) => void;
};

function badgeVariant(status: string): "default" | "secondary" | "success" | "warning" | "danger" | "outline" {
  const normalized = status.toLowerCase();
  if (["high", "critical", "failed", "denied", "inactive"].includes(normalized)) {
    return "danger";
  }
  if (["medium", "warning", "pending", "limited"].includes(normalized)) {
    return "warning";
  }
  if (["success", "succeeded", "active", "enabled"].includes(normalized)) {
    return "success";
  }
  return "secondary";
}

function fieldEntries(row: EvidenceRow) {
  return Object.entries(row.fields).filter(([, value]) => value !== null && value !== undefined && value !== "");
}

const WHEEL_LINE_DELTA_PX = 40;
const WHEEL_PAGE_DELTA_PX = 800;
const MIN_SCROLLBAR_THUMB_PX = 48;

type HorizontalWheelInput = {
  currentScrollLeft: number;
  deltaMode?: number;
  deltaX: number;
  deltaY: number;
  maxScrollLeft: number;
};

type HorizontalDragInput = {
  initialScrollLeft: number;
  maxScrollLeft: number;
  pointerDeltaX: number;
  thumbWidth: number;
  trackWidth: number;
};

type ScrollMetrics = {
  contentWidth: number;
  scrollLeft: number;
  viewportWidth: number;
};

type ScrollbarThumbMetrics = {
  hidden: boolean;
  leftPx: number;
  widthPx: number;
};

type ScrollbarDragState = {
  maxScrollLeft: number;
  pointerId: number;
  scrollLeft: number;
  thumbWidth: number;
  trackWidth: number;
  x: number;
};

export function calculateEvidenceTableHorizontalWheelUpdate({
  currentScrollLeft,
  deltaMode = 0,
  deltaX,
  deltaY,
  maxScrollLeft,
}: HorizontalWheelInput): { nextScrollLeft: number; shouldPreventDefault: boolean } {
  const max = Math.max(0, maxScrollLeft);
  const current = Math.min(max, Math.max(0, currentScrollLeft));

  if (max === 0) {
    return { nextScrollLeft: current, shouldPreventDefault: false };
  }

  const rawDelta = Math.abs(deltaX) > Math.abs(deltaY) ? deltaX : deltaY;
  if (rawDelta === 0) {
    return { nextScrollLeft: current, shouldPreventDefault: false };
  }

  const multiplier = deltaMode === 1 ? WHEEL_LINE_DELTA_PX : deltaMode === 2 ? WHEEL_PAGE_DELTA_PX : 1;
  const delta = rawDelta * multiplier;
  const canMoveLeft = delta < 0 && current > 0;
  const canMoveRight = delta > 0 && current < max;

  if (!canMoveLeft && !canMoveRight) {
    return { nextScrollLeft: current, shouldPreventDefault: false };
  }

  return {
    nextScrollLeft: Math.min(max, Math.max(0, current + delta)),
    shouldPreventDefault: true,
  };
}

export function calculateEvidenceTableScrollbarThumb({
  contentWidth,
  scrollLeft,
  trackWidth,
  viewportWidth,
}: ScrollMetrics & { trackWidth: number }): ScrollbarThumbMetrics {
  if (contentWidth <= viewportWidth || trackWidth <= 0) {
    return { hidden: true, leftPx: 0, widthPx: trackWidth };
  }

  const maxScrollLeft = contentWidth - viewportWidth;
  const thumbWidth = Math.min(
    trackWidth,
    Math.max(MIN_SCROLLBAR_THUMB_PX, (viewportWidth / contentWidth) * trackWidth),
  );
  const maxThumbLeft = Math.max(0, trackWidth - thumbWidth);
  const scrollRatio = maxScrollLeft === 0 ? 0 : Math.min(1, Math.max(0, scrollLeft / maxScrollLeft));

  return {
    hidden: false,
    leftPx: maxThumbLeft * scrollRatio,
    widthPx: thumbWidth,
  };
}

export function calculateEvidenceTableDragScrollLeft({
  initialScrollLeft,
  maxScrollLeft,
  pointerDeltaX,
  thumbWidth,
  trackWidth,
}: HorizontalDragInput): number {
  const max = Math.max(0, maxScrollLeft);
  if (max === 0) {
    return 0;
  }

  const maxThumbLeft = Math.max(1, trackWidth - thumbWidth);
  const scrollPerPixel = max / maxThumbLeft;
  return Math.min(max, Math.max(0, initialScrollLeft + pointerDeltaX * scrollPerPixel));
}

export function EvidenceTable({
  title,
  description,
  rows,
  page,
  emptyTitle,
  loading = false,
  desktopMinWidth = 720,
  importantFields = [],
  onSelectRow,
}: EvidenceTableProps) {
  const tableScrollRef = React.useRef<HTMLDivElement | null>(null);
  const tableRef = React.useRef<HTMLTableElement | null>(null);
  const scrollbarTrackRef = React.useRef<HTMLDivElement | null>(null);
  const dragStateRef = React.useRef<ScrollbarDragState | null>(null);
  const dragCleanupRef = React.useRef<(() => void) | null>(null);
  const scrollbarId = React.useId();
  const tableScrollId = React.useId();
  const [scrollMetrics, setScrollMetrics] = React.useState<ScrollMetrics>({
    contentWidth: desktopMinWidth,
    scrollLeft: 0,
    viewportWidth: desktopMinWidth,
  });
  const headers = rows[0] ? Object.keys(rows[0].fields) : [];
  const importantFieldSet = new Set(importantFields.map((field) => field.toLowerCase()));
  const tableMeasurementKey = `${desktopMinWidth}:${headers.join("|")}:${rows
    .map((row) => `${row.id}:${Object.keys(row.fields).join(",")}`)
    .join("|")}`;
  const maxScrollLeft = Math.max(0, scrollMetrics.contentWidth - scrollMetrics.viewportWidth);
  const visualScrollLeft = Math.min(maxScrollLeft, Math.max(0, scrollMetrics.scrollLeft));
  const scrollbarTrackWidth = scrollbarTrackRef.current?.clientWidth ?? scrollMetrics.viewportWidth;
  const thumbMetrics = calculateEvidenceTableScrollbarThumb({
    ...scrollMetrics,
    scrollLeft: visualScrollLeft,
    trackWidth: scrollbarTrackWidth,
  });

  const measureScrollWidth = React.useCallback(() => {
    const tableScroll = tableScrollRef.current;
    const tableWidth = tableRef.current?.scrollWidth ?? 0;
    const scrollWidth = tableScroll?.scrollWidth ?? 0;
    const viewportCandidates = [
      tableScroll?.clientWidth,
      tableScroll?.getBoundingClientRect().width,
      tableScroll?.parentElement?.clientWidth,
    ].filter((value): value is number => typeof value === "number" && value > 0);
    const viewportWidth = Math.floor(
      viewportCandidates.length > 0 ? Math.min(...viewportCandidates) : scrollbarTrackRef.current?.clientWidth ?? desktopMinWidth,
    );
    const contentWidth = Math.ceil(Math.max(desktopMinWidth, tableWidth, scrollWidth));

    setScrollMetrics((current) => {
      const nextMaxScrollLeft = Math.max(0, contentWidth - viewportWidth);
      const nativeScrollLeft = tableScroll?.scrollLeft ?? 0;
      return {
        contentWidth,
        scrollLeft: Math.min(nextMaxScrollLeft, nativeScrollLeft > 0 ? nativeScrollLeft : current.scrollLeft),
        viewportWidth,
      };
    });
  }, [desktopMinWidth]);

  const syncScrollPosition = React.useCallback(() => {
    const tableScroll = tableScrollRef.current;

    if (!tableScroll) {
      return;
    }

    setScrollMetrics((current) => {
      if (tableScroll.scrollLeft === 0 && current.scrollLeft > 0) {
        return current;
      }

      return {
        ...current,
        scrollLeft: tableScroll.scrollLeft,
      };
    });
  }, []);

  const setHorizontalScrollLeft = React.useCallback(
    (nextScrollLeft: number) => {
      const tableScroll = tableScrollRef.current;
      const liveViewportCandidates = [
        tableScroll?.clientWidth,
        tableScroll?.getBoundingClientRect().width,
        tableScroll?.parentElement?.clientWidth,
      ].filter((value): value is number => typeof value === "number" && value > 0);
      const liveViewportWidth = Math.floor(
        liveViewportCandidates.length > 0
          ? Math.min(...liveViewportCandidates)
          : scrollbarTrackRef.current?.clientWidth ?? scrollMetrics.viewportWidth,
      );
      const liveContentWidth = Math.ceil(
        Math.max(desktopMinWidth, scrollMetrics.contentWidth, tableRef.current?.scrollWidth ?? 0, tableScroll?.scrollWidth ?? 0),
      );
      const max = Math.max(0, liveContentWidth - liveViewportWidth, scrollMetrics.contentWidth - scrollMetrics.viewportWidth);
      const clamped = Math.min(max, Math.max(0, nextScrollLeft));

      if (tableScroll) {
        tableScroll.scrollLeft = clamped;
      }
      setScrollMetrics((current) => ({
        ...current,
        contentWidth: liveContentWidth,
        scrollLeft: clamped,
        viewportWidth: liveViewportWidth,
      }));
    },
    [desktopMinWidth, scrollMetrics.contentWidth, scrollMetrics.viewportWidth],
  );

  const scrollToTrackClientX = React.useCallback(
    (clientX: number) => {
      const track = scrollbarTrackRef.current;
      if (!track || thumbMetrics.hidden) {
        return;
      }

      const rect = track.getBoundingClientRect();
      const maxThumbLeft = Math.max(1, rect.width - thumbMetrics.widthPx);
      const thumbLeft = Math.min(maxThumbLeft, Math.max(0, clientX - rect.left - thumbMetrics.widthPx / 2));
      setHorizontalScrollLeft((thumbLeft / maxThumbLeft) * maxScrollLeft);
    },
    [maxScrollLeft, setHorizontalScrollLeft, thumbMetrics.hidden, thumbMetrics.widthPx],
  );

  const handleHorizontalWheel = React.useCallback(
    (event: WheelEvent) => {
      const update = calculateEvidenceTableHorizontalWheelUpdate({
        currentScrollLeft: visualScrollLeft,
        deltaMode: event.deltaMode,
        deltaX: event.deltaX,
        deltaY: event.deltaY,
        maxScrollLeft,
      });

      if (!update.shouldPreventDefault) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      setHorizontalScrollLeft(update.nextScrollLeft);
    },
    [maxScrollLeft, setHorizontalScrollLeft, visualScrollLeft],
  );

  React.useEffect(() => {
    const tableScroll = tableScrollRef.current;

    if (loading || rows.length === 0 || !tableScroll) {
      return;
    }

    const options: AddEventListenerOptions = { passive: false };
    tableScroll.addEventListener("wheel", handleHorizontalWheel, options);

    return () => {
      tableScroll.removeEventListener("wheel", handleHorizontalWheel, options);
    };
  }, [handleHorizontalWheel, loading, rows.length]);

  React.useEffect(() => {
    measureScrollWidth();

    const table = tableRef.current;
    const tableScroll = tableScrollRef.current;
    const scrollbarTrack = scrollbarTrackRef.current;
    const frame = window.requestAnimationFrame(measureScrollWidth);

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measureScrollWidth);
      return () => {
        window.cancelAnimationFrame(frame);
        window.removeEventListener("resize", measureScrollWidth);
      };
    }

    const observer = new ResizeObserver(measureScrollWidth);
    if (table) observer.observe(table);
    if (tableScroll) observer.observe(tableScroll);
    if (scrollbarTrack) observer.observe(scrollbarTrack);
    window.addEventListener("resize", measureScrollWidth);

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", measureScrollWidth);
    };
  }, [measureScrollWidth, tableMeasurementKey]);

  const handleScrollbarKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      const step = 96;
      const pageStep = Math.max(240, scrollMetrics.viewportWidth * 0.75);

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setHorizontalScrollLeft(visualScrollLeft - step);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setHorizontalScrollLeft(visualScrollLeft + step);
      } else if (event.key === "PageUp") {
        event.preventDefault();
        setHorizontalScrollLeft(visualScrollLeft - pageStep);
      } else if (event.key === "PageDown") {
        event.preventDefault();
        setHorizontalScrollLeft(visualScrollLeft + pageStep);
      } else if (event.key === "Home") {
        event.preventDefault();
        setHorizontalScrollLeft(0);
      } else if (event.key === "End") {
        event.preventDefault();
        setHorizontalScrollLeft(maxScrollLeft);
      }
    },
    [maxScrollLeft, scrollMetrics.viewportWidth, setHorizontalScrollLeft, visualScrollLeft],
  );

  const handleThumbPointerDown = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      const tableScroll = tableScrollRef.current;
      const track = scrollbarTrackRef.current;
      if (!track) {
        return;
      }

      const dragMaxScrollLeft = Math.max(
        0,
        maxScrollLeft,
        tableScroll ? tableScroll.scrollWidth - tableScroll.clientWidth : 0,
        tableScroll ? desktopMinWidth - tableScroll.clientWidth : 0,
      );
      dragStateRef.current = {
        maxScrollLeft: dragMaxScrollLeft,
        pointerId: event.pointerId,
        scrollLeft: visualScrollLeft,
        thumbWidth: thumbMetrics.widthPx,
        trackWidth: track.clientWidth,
        x: event.clientX,
      };

      dragCleanupRef.current?.();

      const handleWindowPointerMove = (moveEvent: PointerEvent) => {
        const dragState = dragStateRef.current;
        if (!dragState || moveEvent.pointerId !== dragState.pointerId) {
          return;
        }

        moveEvent.preventDefault();
        setHorizontalScrollLeft(
          calculateEvidenceTableDragScrollLeft({
            initialScrollLeft: dragState.scrollLeft,
            maxScrollLeft: dragState.maxScrollLeft,
            pointerDeltaX: moveEvent.clientX - dragState.x,
            thumbWidth: dragState.thumbWidth,
            trackWidth: dragState.trackWidth,
          }),
        );
      };

      const handleWindowPointerUp = (upEvent: PointerEvent) => {
        const dragState = dragStateRef.current;
        if (dragState?.pointerId !== upEvent.pointerId) {
          return;
        }

        dragStateRef.current = null;
        dragCleanupRef.current?.();
      };

      window.addEventListener("pointermove", handleWindowPointerMove, { passive: false });
      window.addEventListener("pointerup", handleWindowPointerUp);
      window.addEventListener("pointercancel", handleWindowPointerUp);
      dragCleanupRef.current = () => {
        window.removeEventListener("pointermove", handleWindowPointerMove);
        window.removeEventListener("pointerup", handleWindowPointerUp);
        window.removeEventListener("pointercancel", handleWindowPointerUp);
        dragCleanupRef.current = null;
      };

      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch {
        // Pointer capture can fail if the browser has already cancelled the pointer.
      }
    },
    [desktopMinWidth, maxScrollLeft, setHorizontalScrollLeft, thumbMetrics.widthPx, visualScrollLeft],
  );

  React.useEffect(() => () => dragCleanupRef.current?.(), []);

  const handleThumbPointerMove = React.useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const dragState = dragStateRef.current;

      if (!dragState || event.pointerId !== dragState.pointerId) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      setHorizontalScrollLeft(
        calculateEvidenceTableDragScrollLeft({
          initialScrollLeft: dragState.scrollLeft,
          maxScrollLeft: dragState.maxScrollLeft,
          pointerDeltaX: event.clientX - dragState.x,
          thumbWidth: dragState.thumbWidth,
          trackWidth: dragState.trackWidth,
        }),
      );
    },
    [setHorizontalScrollLeft],
  );

  const handleThumbPointerUp = React.useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const dragState = dragStateRef.current;
    if (dragState?.pointerId !== event.pointerId) {
      return;
    }

    dragStateRef.current = null;
    dragCleanupRef.current?.();
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // The pointer may already have been released by the browser.
    }
  }, []);

  return (
    <Card className="admin-card">
      <CardHeader className="gap-2">
        <div className="topbar-row">
          <div className="admin-card-copy">
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          {page ? (
            <Badge variant="outline">
              {page.offset + 1}-{page.offset + rows.length} of bounded page
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="min-w-0">
        {loading ? (
          <div className="space-y-3" aria-label="Loading evidence">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : rows.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-[var(--border)] p-6 text-sm text-[var(--muted-foreground)]">
            <p className="font-semibold text-[var(--foreground)]">{emptyTitle}</p>
            <p className="mt-1">Backend returned an empty bounded page for this surface.</p>
          </div>
        ) : (
          <>
            <div className="hidden min-w-0 md:block">
              <div className="evidence-table-scroll-shell">
                <div
                  aria-label={`${title} table horizontal scroll`}
                  className="evidence-table-scroll"
                  id={tableScrollId}
                  onScroll={syncScrollPosition}
                  ref={tableScrollRef}
                  tabIndex={0}
                >
                  <div
                    className="evidence-table-scroll-content"
                    style={{
                      minWidth: `${desktopMinWidth}px`,
                      transform: `translateX(${-visualScrollLeft}px)`,
                      width: `${scrollMetrics.contentWidth}px`,
                    }}
                  >
                    <table
                      className="evidence-table border-collapse text-left text-sm"
                      ref={tableRef}
                      style={{ minWidth: `${desktopMinWidth}px` }}
                    >
                      <thead className="bg-[var(--muted)] text-[var(--muted-foreground)]">
                        <tr>
                          {headers.map((header) => {
                            const important = importantFieldSet.has(header.toLowerCase());
                            return (
                              <th
                                className={
                                  important
                                    ? "evidence-header-important px-4 py-3 font-semibold"
                                    : "px-4 py-3 font-semibold"
                                }
                                key={header}
                              >
                                {header}
                              </th>
                            );
                          })}
                          <th className="px-4 py-3 font-semibold">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)]">
                        {rows.map((row) => (
                          <tr className="align-top" key={row.id}>
                            {fieldEntries(row).map(([key, value]) => {
                              const normalizedKey = key.toLowerCase();
                              const important = importantFieldSet.has(normalizedKey);
                              return (
                                <td
                                  className={important ? "evidence-cell-important px-4 py-4" : "px-4 py-4"}
                                  key={key}
                                >
                                  {normalizedKey.includes("status") || normalizedKey.includes("severity") ? (
                                    <Badge variant={badgeVariant(String(value))}>{value}</Badge>
                                  ) : normalizedKey.includes("correlation") || normalizedKey.includes("reference") ? (
                                    <code className="rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">{value}</code>
                                  ) : (
                                    value
                                  )}
                                </td>
                              );
                            })}
                            <td className="px-4 py-4">
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => onSelectRow?.(row)}
                              >
                                Details
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div
                  aria-controls={tableScrollId}
                  aria-label={`${title} table horizontal scrollbar`}
                  aria-orientation="horizontal"
                  aria-valuemax={Math.round(maxScrollLeft)}
                  aria-valuemin={0}
                  aria-valuenow={Math.round(visualScrollLeft)}
                  className="evidence-table-drag-scrollbar"
                  id={scrollbarId}
                  onClick={(event) => {
                    if (event.target === event.currentTarget) {
                      scrollToTrackClientX(event.clientX);
                    }
                  }}
                  onKeyDown={handleScrollbarKeyDown}
                  ref={scrollbarTrackRef}
                  role="scrollbar"
                  tabIndex={thumbMetrics.hidden ? -1 : 0}
                >
                  <div
                    aria-hidden="true"
                    className="evidence-table-drag-scrollbar-thumb"
                    onPointerCancel={handleThumbPointerUp}
                    onPointerDown={handleThumbPointerDown}
                    onPointerMove={handleThumbPointerMove}
                    onPointerUp={handleThumbPointerUp}
                    style={{
                      transform: `translateX(${thumbMetrics.leftPx}px)`,
                      width: `${thumbMetrics.widthPx}px`,
                    }}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-3 md:hidden">
              {rows.map((row) => (
                <div className="scope-list-item" key={row.id}>
                  <div className="topbar-row">
                    <div className="admin-card-copy">
                      <p className="font-semibold">{row.primary}</p>
                      <p className="mt-1 text-sm text-[var(--muted-foreground)]">{row.secondary}</p>
                    </div>
                    <Badge variant={badgeVariant(row.status)}>{row.status}</Badge>
                  </div>
                  {row.correlationId ? (
                    <code className="mt-3 inline-block rounded-lg bg-[var(--muted)] px-2 py-1 text-xs">
                      {row.correlationId}
                    </code>
                  ) : null}
                  <Button
                    className="mt-4 w-full"
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => onSelectRow?.(row)}
                  >
                    Details
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
