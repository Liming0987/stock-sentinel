interface PageHeaderProps {
  kicker: string;
  title: string;
  description?: string;
}

export function PageHeader({ kicker, title, description }: PageHeaderProps) {
  return (
    <div className="mb-[26px]">
      <p className="mb-1.5 text-[12.5px] font-semibold uppercase tracking-[0.1em] text-primary">{kicker}</p>
      <h1 className="font-serif text-[38px] font-medium leading-[1.05] tracking-[-0.02em]">{title}</h1>
      {description && (
        <p className="mt-2.5 max-w-[600px] text-[15px] leading-relaxed text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
