import sys
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr
import maya.cmds as mc


class NSphereClass(omui.MPxLocatorNode):
    '''The NSphere node without any drawing.
    Note the drawing requires Viewport 2.0 as drawing is not implemented in this class.
    Drawing in this class would only be performed in the legacy viewport.
    '''

    # Node attributes
    m_id = om.MTypeId(0x1001)
    m_drawDbClassification = "drawdb/geometry/NSphere"
    m_drawRegistrantId = "NSphereNodePlugin"

    # Dummy attribute to connect NSpheres
    m_parent = None
    m_child = None
    # Attribute to connect to a SdCapsuleData node
    m_outSdCapsule = None

    @staticmethod
    def creator():
        '''This is required by Maya to create an instance of the class'''

        return NSphereClass()

    @staticmethod
    def initialize():
        '''Initialise the node'''

        numericAttr = om.MFnNumericAttribute()

        NSphereClass.m_parent = numericAttr.create("parentN", "pn", om.MFnNumericData.kBoolean)
        numericAttr.writable = True
        numericAttr.storable = True
        numericAttr.hidden = False
        numericAttr.keyable = False
        om.MPxNode.addAttribute(NSphereClass.m_parent)

        NSphereClass.m_child = numericAttr.create("childN", "cn", om.MFnNumericData.kBoolean)
        numericAttr.writable = False
        numericAttr.readable = True
        numericAttr.storable = False
        numericAttr.hidden = False
        numericAttr.keyable = False
        om.MPxNode.addAttribute(NSphereClass.m_child)

    def __init__(self):
        '''Constructor'''

        omui.MPxLocatorNode.__init__(self)

    def compute(self, plug, data):
        '''Empty compute function as no computation is necessary'''

        return None


class NSphereClassDrawOverride(omr.MPxDrawOverride):
    '''This class is used for the draw override in Viewport 2.0'''

    @staticmethod
    def creator(obj):
        '''This is required by Maya to create an instance of the class'''

        return NSphereClassDrawOverride(obj)

    def __init__(self, obj):
        '''The constructor.
        The isAlwaysDirty flag in the MPxDrawOverride class is set to false so the draw override is updated when the node is marked dirty
        A callback is added to mark the node as dirty for certain circumstances (via MRenderer::setGeometryDrawDirty())
        '''
        omr.MPxDrawOverride.__init__(self, obj, None, False)

        self.m_CurrentBoundingBox = om.MBoundingBox()
        # Position of self and parent NSphere
        self.m_position = (0, 0, 0)
        self.m_parentPosition = (0, 0, 0)
        # Scale of transform node
        self.m_scale = (1.0, 1.0, 1.0)
        # Radius of self and parent NSphere
        self.m_radius = 1.0
        self.m_parentRadius = 1.0
        # List of centres and radii for each sphere to draw
        self.m_radii = []
        self.m_centres = []

    def supportedDrawAPIs(self):
        '''Let Maya know which APIs can be used. In this case is OpenGL and DirectX'''

        return omr.MRenderer.kOpenGL | omr.MRenderer.kDirectX11 | omr.MRenderer.kOpenGLCoreProfile

    def isBounded(self, objPath, cameraPath):
        '''Let Maya know that the object has a bounding box'''

        return True

    def disableInternalBoundingBoxDraw(self):
        '''Perform custom bounding box drawing'''

        return True

    def boundingBox(self, objPath, cameraPath):
        '''Calculate the bounding box.

        Args:
            objPath: The DAG path of the locator
            cameraPath: The DAG path of the current camera
        '''

        corner1 = om.MPoint(-0.5, -0.5, -0.5)
        corner2 = om.MPoint(0.5, 0.5, 0.5)

        self.getScale(objPath)
        corner1 *= self.m_radius
        corner2 *= self.m_radius

        self.m_CurrentBoundingBox.clear()
        self.m_CurrentBoundingBox.expand(corner1)
        self.m_CurrentBoundingBox.expand(corner2)

        return self.m_CurrentBoundingBox

    def prepareForDraw(self, objPath, cameraPath, frameContext, data):
        '''Cache data before it is drawn'''

        # Get the scale of the object
        self.getScale(objPath)
        # Get the node to retrieve data
        nNode = objPath.node()

        # Get the plug from the parent
        plug = om.MPlug(nNode, NSphereClass.m_parent)
        # If there is a parent NSphere
        if plug.isConnected:
            # Get the position of this node and the parent node
            self.getPosition(objPath)
            self.getParentNSphereData(objPath)
            startPoint = om.MPoint(self.m_position[0], self.m_position[1], self.m_position[2])
            # Negate the offset from the transform node
            parentPoint = om.MPoint(self.m_parentPosition[0], self.m_parentPosition[1], self.m_parentPosition[2])
            # Get the unit direction
            unit = parentPoint - startPoint
            numUnits = unit.length()
            unit /= numUnits
            radiusUnit = (self.m_parentRadius - self.m_radius) / numUnits
            # Lists of the centre and radius of each sphere to draw
            self.m_centres = []
            self.m_radii = []
            # Interpolate the values for the lists
            for i in range(int(numUnits) + 1):
                pos = om.MPoint(unit * i)
                pos.x /= self.m_scale[0]
                pos.y /= self.m_scale[1]
                pos.z /= self.m_scale[2]
                self.m_centres.append(pos)
                rad = (self.m_radius + (radiusUnit * i)) / self.m_radius
                self.m_radii.append(rad)
        # If this is the root, there is only one sphere to draw
        else:
            self.m_centres = [om.MPoint(0.0, 0.0, 0.0)]
            self.m_radii = [1.0]

    def hasUIDrawables(self):
        '''This function queries if the function addUIDrawables will be called'''

        return True

    def addUIDrawables(self, objPath, drawManager, frameContext, data):
        '''This function is the draw call.

        Args:
            objPath: The DAG path to the locator node
            drawManager: The MUIDrawManager object used for drawing
            frameContext: A frame context
            data: The data required to draw
        '''

        drawManager.beginDrawable()

        # Draw the foot print solid/wireframe
        # drawManager.setColor(locatordata.fColor)
        colour = om.MColor()
        colour.g = 1.0
        drawManager.setColor(colour)
        drawManager.setDepthPriority(5)

        if (frameContext.getDisplayStyle() & omr.MFrameContext.kGouraudShaded):
            for centre, radius in zip(self.m_centres, self.m_radii):
                drawManager.sphere(centre, radius, True)

        else:
            for centre, radius in zip(self.m_centres, self.m_radii):
                drawManager.sphere(centre, radius, False)

        drawManager.endDrawable()

    def getScale(self, objPath):
        '''Get the scale of the transform node.

        Args:
            objPath: The DAG path for this locator
        '''

        # Get the current node and attach to a DAG node function set
        nNode = objPath.node()
        dagFn = om.MFnDagNode(nNode)
        # Get the parent (transform) node and attach to the DAG function set
        parentObj = dagFn.parent(0)
        dagFn.setObject(parentObj)
        # Get the name of the transform node and find the scale attribute
        nodeName = dagFn.name()
        self.m_scale = mc.getAttr(nodeName + ".scale")[0]
        self.m_radius = max(self.m_scale)

    def getPosition(self, objPath):
        '''Get the position of the transform node

        Args:
            objPath: The DAG path for this locator
        '''

        # Get the current node and attach to a DAG node function set
        nNode = objPath.node()
        dagFn = om.MFnDagNode(nNode)
        # Get the parent (transform) node and attach to the DAG function set
        parentObj = dagFn.parent(0)
        dagFn.setObject(parentObj)
        # Get the name of the transform node and find the position attribute
        nodeName = dagFn.name()
        self.m_position = mc.getAttr(nodeName + ".translate")[0]

    def getParentNSphereData(self, objPath):
        '''Get the position and radius of the transform node from the parent NSphere

        Args:
            objPath: The DAG path for this locator
        '''

        nNode = objPath.node()
        # Get the plug from the parent
        plug = om.MPlug(nNode, NSphereClass.m_parent).source()
        # Get the node that it belongs to
        node = plug.node()
        dagFn = om.MFnDagNode(node)
        # Get the parent (transform node)
        parentObj = dagFn.parent(0)
        dagFn.setObject(parentObj)
        # Get the node name
        nodeName = dagFn.name()
        self.m_parentPosition = mc.getAttr(nodeName + ".translate")[0]
        self.m_parentRadius = max(mc.getAttr(nodeName + ".scale")[0])


def maya_useNewAPI():
    '''Tell Maya to use the Python API 2.0.'''

    pass


def initializePlugin(obj):
    '''Initialise the plugin when Maya loads it'''

    plugin = om.MFnPlugin(obj)

    try:
        plugin.registerNode("NSphere", NSphereClass.m_id, NSphereClass.creator, NSphereClass.initialize, om.MPxNode.kLocatorNode, NSphereClass.m_drawDbClassification)
    except:
        sys.stderr.write("Failed to register node\n")
        raise

    try:
        omr.MDrawRegistry.registerDrawOverrideCreator(NSphereClass.m_drawDbClassification, NSphereClass.m_drawRegistrantId, NSphereClassDrawOverride.creator)
    except:
        sys.stderr.write("Failed to register override\n")
        raise


def uninitializePlugin(obj):
    '''Uninitialise the plugin when Maya unloads it'''

    plugin = om.MFnPlugin(obj)

    try:
        plugin.deregisterNode(NSphereClass.m_id)
    except:
        sys.stderr.write("Failed to deregister node\n")
        pass

    try:
        omr.MDrawRegistry.deregisterDrawOverrideCreator(NSphereClass.m_drawDbClassification, NSphereClass.m_drawRegistrantId)
    except:
        sys.stderr.write("Failed to deregister override\n")
        pass
