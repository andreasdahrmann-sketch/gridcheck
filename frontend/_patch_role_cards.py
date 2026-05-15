from pathlib import Path

p = Path(__file__).with_name("app/page.tsx")
text = p.read_text(encoding="utf-8")

start = text.index('            <div className="mb-8 grid gap-4 lg:grid-cols-3">')
end = text.index("            <ProductDecisionGuide", start)

new_block = '''            <div className="mb-8 grid gap-4 lg:grid-cols-3">
              {ROLE_CARDS.map((item) => {
                const cardClassName = `rounded-[24px] border p-5 transition ${
                  item.active
                    ? "border-brand-cyan/30 bg-brand-cyan/10 hover:bg-brand-cyan/15"
                    : "border-white/10 bg-white/5 opacity-90"
                }`;

                const badge = (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${
                      item.active
                        ? "border border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan"
                        : "border border-amber-400/25 bg-amber-400/10 text-amber-200"
                    }`}
                  >
                    {item.status}
                  </span>
                );

                const body = (
                  <>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-lg font-semibold text-white">{item.title}</p>
                        {item.subtitle ? (
                          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-text-dim">{item.subtitle}</p>
                        ) : null}
                      </div>
                      {badge}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-text-muted">{item.description}</p>
                    <div
                      className={`mt-4 inline-flex items-center text-sm font-semibold ${
                        item.active ? "text-white" : "text-text-muted"
                      }`}
                    >
                      {item.cta}
                      {item.active ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
                    </div>
                  </>
                );

                if (item.active && "href" in item) {
                  return (
                    <Link key={item.title} href={item.href} className={cardClassName}>
                      {body}
                    </Link>
                  );
                }

                return (
                  <div
                    key={item.title}
                    role="group"
                    aria-disabled="true"
                    aria-label={`${item.title}: ${item.status}`}
                    className={cardClassName}
                  >
                    {body}
                  </div>
                );
              })}
            </div>

'''

text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("patched", start, end)
