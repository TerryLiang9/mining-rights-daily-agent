import { createReport } from "./agent-api.js";
import { formatReportOutput, parseCommand, usage } from "./format.js";

async function main(args: string[]): Promise<void> {
  const parsed = parseCommand(args);
  if (parsed.command !== "report" || parsed.query.length === 0) {
    console.error(usage());
    process.exitCode = 1;
    return;
  }

  const report = await createReport(parsed.query, { pdfUrl: parsed.pdfUrl });
  console.log(formatReportOutput(report));
}

main(process.argv.slice(2)).catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
