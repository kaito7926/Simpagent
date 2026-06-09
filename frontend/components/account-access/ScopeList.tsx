type ScopeListProps = {
  scopes: string[];
  labels: Record<string, string>;
};

export function ScopeList({ scopes, labels }: ScopeListProps) {
  return (
    <ul className="scope-list">
      {scopes.map((scope) => (
        <li className="scope-list-item" key={scope}>
          <span className="scope-label">{labels[scope] ?? scope}</span>
          <span className="scope-code">{scope}</span>
        </li>
      ))}
    </ul>
  );
}
