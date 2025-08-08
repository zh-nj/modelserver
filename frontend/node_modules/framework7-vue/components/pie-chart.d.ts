
import { ComponentOptionsMixin, DefineComponent, PropType } from 'vue';


declare const PieChart: DefineComponent<
  {
    
    tooltip: {
      type: BooleanConstructor;
    },

    formatTooltip: {
      type: FunctionConstructor;
    },

    size: {
      type: NumberConstructor;
      default: number;
    },

    datasets: {
      type: ArrayConstructor;
      default: () => [];
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

export default PieChart;
  