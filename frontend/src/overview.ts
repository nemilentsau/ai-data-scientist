import { latestAttempt, type ArtifactSummary } from "./artifactLoop";
import { humanizeId } from "./format";
import type { LoadedRun } from "./types";

export type GalleryItem = {
  artifactId: string;
  title: string;
  status: string;
  purpose: string;
  chartFamily: string;
  imageUrl?: string;
};

export function toGalleryItems(run: LoadedRun, summaries: ArtifactSummary[]): GalleryItem[] {
  return summaries.map((summary) => {
    const attempt = latestAttempt(summary);
    const renderPath = attempt?.paths.renderImage;
    const image = renderPath ? run.files.get(renderPath) : undefined;
    const imageUrl = image?.kind === "image" ? image.url : undefined;

    return {
      artifactId: summary.id,
      title: humanizeId(summary.id),
      status: summary.status,
      purpose: summary.plan?.purpose ?? "",
      chartFamily: summary.plan?.expected_chart_family ?? "chart",
      ...(imageUrl ? { imageUrl } : {}),
    };
  });
}
