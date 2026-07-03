import { ImageOff } from "lucide-react";

import type { GalleryItem } from "./overview";
import { EmptyNote, StatusChip } from "./ui";

export function ChartGallery({
  items,
  onSelect,
}: {
  items: GalleryItem[];
  onSelect: (artifactId: string) => void;
}) {
  if (items.length === 0) {
    return <EmptyNote>No chart artifacts were produced for this run.</EmptyNote>;
  }

  return (
    <div className="grid gap-x-8 gap-y-12 lg:grid-cols-2">
      {items.map((item) => (
        <figure key={item.artifactId} className="space-y-3">
          <button
            type="button"
            onClick={() => onSelect(item.artifactId)}
            className="block w-full overflow-hidden rounded-lg border border-zinc-200 bg-white transition hover:border-teal-300 hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
            aria-label={`Open ${item.title}`}
          >
            {item.imageUrl ? (
              <img src={item.imageUrl} alt={item.title} className="h-full w-full object-contain p-3" />
            ) : (
              <span className="flex h-44 items-center justify-center gap-2 text-sm text-zinc-400">
                <ImageOff size={18} />
                No rendered chart
              </span>
            )}
          </button>
          <figcaption className="space-y-1.5">
            <div className="flex items-start justify-between gap-3">
              <button
                type="button"
                onClick={() => onSelect(item.artifactId)}
                className="text-left text-base font-semibold tracking-tight text-zinc-950 hover:text-teal-800"
              >
                {item.title}
              </button>
              <StatusChip status={item.status} />
            </div>
            {item.purpose ? (
              <p className="text-sm leading-6 text-zinc-600">{item.purpose}</p>
            ) : null}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
