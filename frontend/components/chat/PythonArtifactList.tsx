import { Download, FileImage, FileJson2, FileSpreadsheet, FileText } from "lucide-react";

import { ARTIFACT_SECTION_LABEL } from "@/lib/chat/tool-copy";
import type { PresentedArtifact } from "@/lib/chat/tool-results";

type PythonArtifactListProps = {
  artifacts: PresentedArtifact[];
};

function iconForType(typeLabel: string) {
  switch (typeLabel) {
    case "CSV":
      return <FileSpreadsheet size={16} strokeWidth={1.75} />;
    case "JSON":
      return <FileJson2 size={16} strokeWidth={1.75} />;
    case "PNG":
      return <FileImage size={16} strokeWidth={1.75} />;
    default:
      return <FileText size={16} strokeWidth={1.75} />;
  }
}

export function PythonArtifactList({ artifacts }: PythonArtifactListProps) {
  if (artifacts.length === 0) {
    return null;
  }

  return (
    <section className="python-artifact-panel" aria-label={ARTIFACT_SECTION_LABEL}>
      <p className="python-section-label">{ARTIFACT_SECTION_LABEL}</p>
      <ul className="python-artifact-list">
        {artifacts.map((artifact) => (
          <li className="python-artifact-item" key={artifact.artifactId}>
            <div className="python-artifact-copy">
              <span className="python-artifact-icon" aria-hidden="true">
                {iconForType(artifact.typeLabel)}
              </span>
              <div className="python-artifact-text">
                <span className="python-artifact-name">{artifact.name}</span>
                <span className="python-artifact-meta">
                  {artifact.typeLabel} · {artifact.sizeLabel}
                </span>
              </div>
            </div>
            <a className="python-artifact-link" download href={artifact.href}>
              <Download size={16} strokeWidth={1.75} aria-hidden="true" />
              <span>Download</span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
