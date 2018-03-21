import math
import maya.api.OpenMaya as om
import maya.cmds as mc


class PointCloudExporter(object):
    '''Class used for calculating the point cloud data and exporting to a file.'''

    def export(self, _folderPath, _fileName, _voxelSize, _smoothness):
        rootNode = self.findFromSelection()
        if rootNode is not None:
            lineSegments = self.findLineSegments(rootNode)
            if len(lineSegments) > 7:
                bbox = self.findBoundingBox(lineSegments, _voxelSize)
                points = self.sampleSD(lineSegments, _voxelSize, _smoothness, bbox)
                fileDir = _folderPath + "/" + _fileName
                self.write(fileDir, points)
                print "File written."

    def findFromSelection(self):
        '''Find the first selected object'''
        selectionList = om.MGlobal.getActiveSelectionList()
        iterator = om.MItSelectionList(selectionList, om.MFn.kDependencyNode)
        if iterator.isDone():
            print "Error. Nothing selected."
            return None
        else:
            node = iterator.getDependNode()
            return node

    def findLineSegments(self, _rootNode):
        '''Find each pair of NSphere nodes and find line segments data.

        Args:
            _rootNode: The root NSphere node

        Returns:
            list: The line segments data as one list with the format[position, radius, position, radius]
        '''

        # Nodes that have already been checked
        checkedN = om.MObjectArray()
        # Nodes that need to be checked
        uncheckedN = om.MObjectArray()
        uncheckedN.append(_rootNode)

        # Create a dependency node and DAG node function set
        dependencyFn = om.MFnDependencyNode()
        dagFn = om.MFnDagNode()

        # Store the line segments data as [parent position, parent radius, child position, child radius]
        # Note position is not a list or tuple, it is 3 values
        lineSegments = []

        # Loop through the node tree and find the line segments and children
        while (len(uncheckedN) > 0):
            # Add the last node to the checked list and remove from unchecked list
            node = uncheckedN[-1]
            uncheckedN.remove(-1)
            checkedN.append(node)

            # Set the dependency node to the last item in the unchecked list
            dependencyFn.setObject(node)
            # print dependencyFn.name()

            # Find the parent and line segment
            parentNAttr = dependencyFn.attribute("parentN")
            nPlug = om.MPlug(node, parentNAttr).source()
            if not nPlug.isNull:
                # Get the parent NSphere node
                n = nPlug.node()
                dagFn.setObject(n)
                # Get the transform node
                p = dagFn.parent(0)
                dagFn.setObject(p)
                transformName = dagFn.name()
                # Get the data from the node
                pos = mc.getAttr(transformName + ".translate")[0]
                parentData = [i for i in pos]
                parentData.append(max(mc.getAttr(transformName + ".scale")[0]))

                # Get the current NSphere and find the transform
                dagFn.setObject(node)
                p = dagFn.parent(0)
                dagFn.setObject(p)
                transformName = dagFn.name()
                # Get the data
                pos = mc.getAttr(transformName + ".translate")[0]
                childData = [i for i in pos]
                childData.append(max(mc.getAttr(transformName + ".scale")[0]))

                # Add to the line segments data
                lineSegments += parentData
                lineSegments += childData

            # Find the child nodes
            childNAttr = dependencyFn.attribute("childN")
            nPlug = om.MPlug(node, childNAttr)
            childPlugs = nPlug.destinations()
            for p in childPlugs:
                n = p.node()
                if n not in checkedN:
                    uncheckedN.append(n)

        # Return the list of line segments data
        return lineSegments

    def findBoundingBox(self, _sdCapsuleData, _voxelSize):
        '''Find the bounding box from the sd capsule data.

        Args:
            _sdCapsuleData: A list of the sdCapsule data.
            _voxelSize: The size of the voxels

        Returns:
            tuple, tuple: The min and max coordinate (x,y,z) for the bounding box as a multiple of the voxel size.
        '''

        # Note the list is in the format [x, y, z, r, x, y, z, r, ...]
        # Split list into list of lists, i.e [[x,y,z,r, x,y,z,r], ...]
        # This is 8 values long as it is the [parent, child] data.
        # Only the child data is needed as parents can be children of other nodes and can often be duplicated.
        sdData = zip(*[iter(_sdCapsuleData)] * 8)
        # Get the x,y,z values from the sdData after adding/subtracting the radius at each point
        # This is a list of tuples as [(x-r, x+r, y-r, y+r, z-r, z+r)]
        xyz = [(d[4] - d[7], d[4] + d[7], d[5] - d[7], d[5] + d[7], d[6] - d[7], d[6] + d[7]) for d in sdData]
        # Add the first element of sdCapsuleData to this list as it is never a child
        xyz += [(_sdCapsuleData[0] - _sdCapsuleData[3], _sdCapsuleData[0] + _sdCapsuleData[3], _sdCapsuleData[1] - _sdCapsuleData[3], _sdCapsuleData[1] + _sdCapsuleData[3], _sdCapsuleData[2] - _sdCapsuleData[3], _sdCapsuleData[2] + _sdCapsuleData[3])]
        # Transpose this list so it is a list of tuples [(x-r), (x+r), (y-r), (y+r), (z-r), (z+r)]
        xyzT = map(tuple, map(None, *xyz))
        # Find the min/max of all the values
        xyzMin = [max(xyzT[i]) if i % 2 else min(xyzT[i]) for i in range(6)]
        # Scale this list so it is a multiple of the voxel size
        # This extends each value to the next mutliple of the voxel (larger value if positive, smaller value if negative)
        xyz = [math.ceil(v / _voxelSize) * _voxelSize if v > 0 else math.floor(v / _voxelSize) * _voxelSize for v in xyzMin]

        # Calculate the min and max coordinates as the min/max from the lists
        minBB = (xyz[0], xyz[2], xyz[4])
        maxBB = (xyz[1], xyz[3], xyz[5])

        return minBB, maxBB

    def sampleSD(self, _sdCapsuleData, _voxelSize, _smoothness, _boundingBox):
        '''Sample the grid to find all the signed distances.

        Args:
            _sdCapsuleData: The signed distance capsule data.
            _voxelSize: The size of the voxels.
            _smoothness: The smoothness constant (k) for the smin function
            _boundingBox: The bounding box of the ZSpheres

        Returns:
            list: Points that lie inside the mesh
        '''

        # Create an empty list of points
        points = []
        # Loop through the space and fill the dict
        for x in self.frange(_boundingBox[0][0], _boundingBox[1][0], _voxelSize):
            for y in self.frange(_boundingBox[0][1], _boundingBox[1][1], _voxelSize):
                for z in self.frange(_boundingBox[0][2], _boundingBox[1][2], _voxelSize):
                    value = self.calculateSD((x, y, z), _sdCapsuleData, _smoothness)
                    if value < 0:
                        points.append((x, y, z))

        return points

    def calculateSD(self, _pos, _sdCapsuleData, _k):
        '''Calculate the signed distance at a position

        Args:
            _pos: The position to check for
            _sdCapsuleData: A list of values for the line segments
            _k: The smoothness constant for the smin function

        Returns:
            float: The signed distance at a position
        '''

        # Convert a 1D list to a 2D list
        sdData = zip(*[iter(_sdCapsuleData)] * 8)
        # Get the signed distances for each capsule function
        sDistances = [self.sdCapsule(_pos, s[0:3], s[3], s[4:7], s[7]) for s in sdData]
        # Get the smooth min from all of these values
        return self.smin(_k, sDistances)

    def sdCapsule(self, _pos, _a, _r1, _b, _r2):
        '''Function for signed distance capsule

        This is based of the function sdCapsule from:
        http://iquilezles.org/www/articles/distfunctions/distfunctions.htm
        And modified with the help of Dr Oleg Fryazinov.

        Args:
            _pos: The position to check
            _a: The first point
            _r1: The radius at the first point
            _b: The second point
            _r2: The radius at the second point

        Returns:
            float: The signed distance to the point
        '''

        # Convert lists to Maya vectors
        pos = om.MVector(_pos)
        a = om.MVector(_a)
        b = om.MVector(_b)

        pa = pos - a
        ba = b - a
        h = (pa * ba) / (ba * ba)
        # Clamp to the range 0 <= h <= 1
        if h > 1.0:
            h = 1.0
        if h < 0.0:
            h = 0.0
        bah = ba * h
        return (pa - bah).length() - _r1 - h * (_r2 - _r1)

    def smin(self, _k, _values):
        '''Smooth min function.

        This is based of the function smin from:
        http://iquilezles.org/www/articles/smin/smin.htm
        And is generalised to n dimensions, where n is the length of the input list _values

        Args:
            _k: Power constant
            _values: List of values to find smooth min from

        Returns:
            float: The smooth min from the list of values
        '''
        minV = min(_values)
        minusK = -_k
        res = 0
        for value in _values:
            res += math.exp(minusK * value)

        result = math.log(res) / _k
        return math.copysign(result, minV)

    def frange(self, _start, _end, _step):
        '''Float range function.

        Args:
            _start: The start of the range
            _end: The end of the range
            _step: The value to increment by

        Returns:
            generator: The float range generator
        '''

        value = _start
        while value < _end:
            yield value
            value += _step

    def write(self, _filePath, _points):
        # Create the output ply file
        outputFile = file(_filePath + ".ply", "w")
        # Write the header
        self.writeLine(outputFile, "ply")
        self.writeLine(outputFile, "format ascii 1.0")
        self.writeLine(outputFile, "comment point cloud data")
        self.writeLine(outputFile, "element vertex " + str(len(_points)))
        self.writeLine(outputFile, "property float x")
        self.writeLine(outputFile, "property float y")
        self.writeLine(outputFile, "property float z")
        self.writeLine(outputFile, "element face 0")
        self.writeLine(outputFile, "property list uchar int vertex_indices")
        self.writeLine(outputFile, "end_header")
        # Loop through the points and write them
        for p in _points:
            self.writeLine(outputFile, "{0} {1} {2}".format(str(p[0]), str(p[1]), str(p[2])))

    def writeLine(self, _file, _text=""):
        _file.write(_text + "\n")
