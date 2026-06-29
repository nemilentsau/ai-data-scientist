export type ArtifactKind = "text" | "image" | "binary";

export type TextArtifact = {
  kind: "text";
  path: string;
  size: number;
  text: string;
};

export type ImageArtifact = {
  kind: "image";
  path: string;
  size: number;
  url: string;
};

export type BinaryArtifact = {
  kind: "binary";
  path: string;
  size: number;
};

export type RunArtifact = TextArtifact | ImageArtifact | BinaryArtifact;

export type RunLineage = {
  status?: string;
  revision_count?: number;
  artifact_statuses?: Record<string, string>;
  dependencies?: Record<string, string[]>;
} & Record<string, unknown>;

export type LoadedRun = {
  rootName: string;
  files: Map<string, RunArtifact>;
  lineage: RunLineage;
  paths: string[];
};

export type StageDefinition = {
  id: string;
  label: string;
  owner: string;
  prefix: string;
};

export type JsonParseResult =
  | {
      ok: true;
      value: unknown;
    }
  | {
      ok: false;
    };
