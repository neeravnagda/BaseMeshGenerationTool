import maya.cmds as mc
import PointCloudExport


class UI(object):
    """The Maya UI for the PointCloudExport class"""

    def __init__(self):
        self.pce = PointCloudExport.PointCloudExporter()
        self.m_windowTitle = "Point Cloud Exporter"
        self.m_window = mc.window()

    def start(self):
        self.close()
        self.reloadUI()
        mc.showWindow(self.m_window)

    def close(self):
        if (mc.window(self.m_window, exists=True)):
            mc.deleteUI(self.m_window)

    def reloadUI(self):
        self.m_window = mc.window(title=self.m_windowTitle, rtf=True)
        self.m_layout = mc.columnLayout(adjustableColumn=True)
        mc.separator(h=5)
        self.m_directory = mc.textFieldButtonGrp(label="Folder Path:", pht="Folder path", buttonLabel="Pick", buttonCommand=self.pickFolder)
        self.m_fileName = mc.textFieldGrp(label="File Name:", pht="File name")
        mc.separator(h=5)
        self.m_voxelSizeControl = mc.floatSliderGrp(label="Voxel Size", field=True, minValue=0.0001, maxValue=1.0, value=0.5, step=0.0001)
        mc.separator(h=5)
        self.m_smoothnessControl = mc.floatSliderGrp(label="Smoothness", field=True, minValue=1.0, maxValue=50.0, value=4.0)
        mc.separator(h=5)
        mc.button(label="Export", command=self.export)
        mc.separator(h=5)
        mc.setParent("..")

    def pickFolder(self, *args):
        # Dialog for picking a folder
        filePath = mc.fileDialog2(fileMode=3, dialogStyle=2, okc="Select Folder")
        # Convert to a string
        filePathStr = str(filePath[0])
        mc.textFieldButtonGrp(self.m_directory, edit=True, text=filePathStr)

    def export(self, *args):
        folderDir = mc.textFieldButtonGrp(self.m_directory, query=True, text=True)
        fileName = mc.textFieldGrp(self.m_fileName, query=True, text=True)
        voxelSize = mc.floatSliderGrp(self.m_voxelSizeControl, query=True, value=True)
        smoothness = mc.floatSliderGrp(self.m_smoothnessControl, query=True, value=True)
        if folderDir != "" and fileName != "":
            self.pce.export(folderDir, fileName, voxelSize, smoothness)
