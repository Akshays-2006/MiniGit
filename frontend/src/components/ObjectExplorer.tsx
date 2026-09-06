import { useEffect, useState } from "react";
import { api, type InspectedObject } from "../api/client";
import "./ObjectExplorer.css";

function ObjectNode({ hash, name, depth }: { hash: string; name: string; depth: number }) {
  const [expanded, setExpanded] = useState(depth === 0);
  const [obj, setObj] = useState<InspectedObject | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!expanded || obj) return;
    api
      .getObject(hash)
      .then(setObj)
      .catch((e) => setError(e.message ?? "Failed to load"));
  }, [expanded, hash, obj]);

  const icon = obj?.type === "commit" ? "◆" : obj?.type === "tree" ? "▸" : "▪";

  return (
    <div className="object-node" style={{ paddingLeft: depth * 16 }}>
      <button className="object-node__row" onClick={() => setExpanded((v) => !v)}>
        <span className={`object-node__icon object-node__icon--${obj?.type ?? "pending"}`}>{icon}</span>
        <span className="object-node__name">{name}</span>
        <span className="object-node__hash mono">{hash.slice(0, 10)}</span>
      </button>

      {expanded && error && <div className="object-node__error">{error}</div>}

      {expanded && obj?.type === "commit" && (
        <div className="object-node__children">
          <ObjectNode hash={obj.tree} name="tree" depth={depth + 1} />
        </div>
      )}

      {expanded && obj?.type === "tree" && (
        <div className="object-node__children">
          {obj.entries.map((e) => (
            <ObjectNode key={e.name} hash={e.hash} name={e.name} depth={depth + 1} />
          ))}
        </div>
      )}

      {expanded && obj?.type === "blob" && (
        <div className="object-node__children">
          <div className="object-node__blob-preview mono" style={{ paddingLeft: (depth + 1) * 16 }}>
            {obj.binary ? (
              <span className="object-node__muted">binary, {obj.size} bytes</span>
            ) : (
              <>
                <span className="object-node__muted">{obj.size} bytes</span>
                <pre>{obj.content}</pre>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ObjectExplorer({ rootHash, rootName }: { rootHash: string; rootName: string }) {
  return (
    <div className="object-explorer">
      <div className="object-explorer__heading">Object graph</div>
      <p className="object-explorer__hint">
        Starting from this {rootName}, following every pointer down to its blobs.
      </p>
      <div className="object-explorer__tree">
        <ObjectNode hash={rootHash} name={rootName} depth={0} />
      </div>
    </div>
  );
}
