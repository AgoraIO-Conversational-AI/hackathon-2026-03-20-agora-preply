import { WidgetType } from "@/lib/constants";
import { ErrorAnalysisWidget } from "./ErrorAnalysisWidget";
import { ThemeMapWidget } from "./ThemeMapWidget";
import { PracticeCardWidget } from "./PracticeCardWidget";
import { DefaultWidget } from "./DefaultWidget";

interface WidgetProps {
  data: Record<string, unknown>;
}

const WIDGET_MAP: Record<string, React.ComponentType<WidgetProps>> = {
  [WidgetType.ERROR_ANALYSIS]: ErrorAnalysisWidget,
  [WidgetType.THEME_MAP]: ThemeMapWidget,
  [WidgetType.PRACTICE_CARD]: PracticeCardWidget,
};

export function WidgetRouter({ data }: WidgetProps) {
  const widgetType = data.widget_type as string;
  const Widget = WIDGET_MAP[widgetType];

  if (!Widget) return <DefaultWidget data={data} />;
  return <Widget data={data} />;
}
