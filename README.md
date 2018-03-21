# BaseMeshGenerationTool

A tool inspired by the ZSphere tool from the program ZBrush.

This tool is for Maya and can run on Windows, Linux and Mac operating systems.

Installation instructions:

1. Copy the files in the plugin folder to the Maya plugin folder.
Or add the following variable to the Maya.env file:
MAYA_PLUG_IN_PATH=
and use the directory to the plugin folder

2. Copy the files in the scripts folder to the Maya scripts folder.

3. Copy the Houdini Digital Asset file to a digital_assets folder.


Usage instructions:

1. Make sure the NSphere.py and the Houdini Engine plugins are enabled.

2. Create the desired NSpheres and connect them.

3. Open the Point Cloud exporter with the following Python script:

import PointCloudExportUI as pceUI
pUI = pceUI.UI()
pUI.start()

4. Pick a folder and write a file name. Adjust the voxel size and smoothness.

5. Select the root NSphere node and then press export.

6. Load the Houdini Digital Asset and load the point cloud file.

7. Press Sync Asset on the Houdini Digital Asset.

8. Adjust the digital asset parameters as required.