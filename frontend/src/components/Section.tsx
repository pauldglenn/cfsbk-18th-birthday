export function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="section">
      <div className="section__header">
        <h2>{title}</h2>
        <a href={`#${id}`} className="section__anchor">
          #
        </a>
      </div>
      <div className="section__body">{children}</div>
    </section>
  );
}

