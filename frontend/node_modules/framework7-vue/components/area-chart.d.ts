
import { ComponentOptionsMixin, DefineComponent, PropType } from 'vue';


declare const AreaChart: DefineComponent<
  {
    
    lineChart: {
      type: BooleanConstructor;
    },

    axis: {
      type: BooleanConstructor;
    },

    tooltip: {
      type: BooleanConstructor;
    },

    legend: {
      type: BooleanConstructor;
    },

    toggleDatasets: {
      type: BooleanConstructor;
    },

    formatAxisLabel: {
      type: FunctionConstructor;
    },

    formatLegendLabel: {
      type: FunctionConstructor;
    },

    formatTooltip: {
      type: FunctionConstructor;
    },

    formatTooltipAxisLabel: {
      type: FunctionConstructor;
    },

    formatTooltipTotal: {
      type: FunctionConstructor;
    },

    formatTooltipDataset: {
      type: FunctionConstructor;
    },

    datasets: {
      type: ArrayConstructor;
      default: () => [];
    },

    axisLabels: {
      type: ArrayConstructor;
      default: () => [];
    },

    width: {
      type: NumberConstructor;
      default: number;
    },

    height: {
      type: NumberConstructor;
      default: number;
    },

    maxAxisLabels: {
      type: NumberConstructor;
      default: number;
    }
  },
  () => JSX.Element,
  unknown,
  {},
  {},
  ComponentOptionsMixin,
  ComponentOptionsMixin,
  ("select")[],
  "select"
>;

export default AreaChart;
  