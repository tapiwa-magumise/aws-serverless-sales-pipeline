import { Composition } from "remotion";
import { Pipeline, TOTAL } from "./Pipeline";

export const Root = () => (
  <Composition id="Pipeline" component={Pipeline} durationInFrames={TOTAL} fps={30} width={1080} height={1350} />
);
