# Original illustrative VIS/HCI compositions

These are synthetic worked examples, not paper results or implemented interface screenshots. No artwork from the studied publications or the user's uploaded reference is redistributed.

`worked-example.csv` contains eight artificial observations. The rectangular brush selects b, c and d. The category counts are A: 1 selected / 4 total; B: 2 selected / 4 total. Both SVG figures preserve these identities. There is no measured improvement, perception model or user study.

`method-detail.svg` explains geometric selection, row identity, membership and linked displays. `interaction-storyboard.svg` shows initial state, action target and visible feedback. The source is editable text/vector SVG. `build_examples.py` regenerates the SVG/spec pairs from the adjacent CSV without network access; it is example authoring code, not a universal academic figure generator.

To use the compositor in an actual paper, the agent writes its own figure and panel descriptions under that paper's workspace/figures, supplies the correct relative artwork path, previews the existing diagrams render operation, and renders after authorization. The operation archives an independent reproduction bundle and retains previous figures. Instructions and scope: [VIS/HCI guide](../../docs/VIS_HCI_FIGURES.md).

Reusing this exact drawing cannot explain an unrelated method. Author the actual research objects, transformations and example before optimizing colour or spacing.
