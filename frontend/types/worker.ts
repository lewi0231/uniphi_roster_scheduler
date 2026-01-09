export type Worker = {
  name: string;
  rate: number;
  percentage?: number;
  actualRate?: number;
  shiftLength?: number;
  actualContribution?: number;
  expectedContribution?: number;
};
