# This script runs a suite of scripts from this project to take a singlenuc context (or trinuc if it's already available) bed file
# and produce the normalized dyad position counts, along with all the relevant intermediate files.

from typing import List
import os, sys
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog, Selections
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import (DataTypeStr, getDataDirectory, 
                                                                  getContext, getIsolatedParentDir)
from benbiohelpers.FileSystemHandling.DirectoryHandling import getFilesInDirectory
from mutperiodpy.ExpandContext import expandContext
from mutperiodpy.GenerateMutationBackground import generateMutationBackground
from mutperiodpy.GenerateNucleosomeMutationBackground import generateNucleosomeMutationBackground
from mutperiodpy.CountNucleosomePositionMutations import countNucleosomePositionMutations
from mutperiodpy.NormalizeMutationCounts import normalizeCounts

# Used to generate the relevant background counts files for normalization before the rest of the analysis.
def generateCustomBackground(customBackgroundDir, nucleosomeMapNames, useSingleNucRadius,
                             includeLinker, useNucGroupRadius):

    print("Generating background counts...")

    customBackgroundMutationFilePath = getFilesInDirectory(customBackgroundDir, DataTypeStr.mutations + ".bed", searchRecursively = False)
    assert customBackgroundMutationFilePath is not None, "No parsed mutation file in the directory " + customBackgroundDir

    runAnalysisSuite((customBackgroundMutationFilePath,), nucleosomeMapNames, "No Normalization", None, 
                        useSingleNucRadius, includeLinker, useNucGroupRadius)

    print ("Finished generating background!\n")


def runAnalysisSuite(mutationFilePaths: List[str], nucleosomeMapNames: List[str], normalizationMethod, customBackgroundDir, 
                     useSingleNucRadius, includeLinker, useNucGroupRadius):

    # Make sure at least one radius was selected.
    if not useNucGroupRadius and not useSingleNucRadius:
        raise ValueError("Must select at least one radius.")

    # Make sure at least one input file was found.
    assert len(mutationFilePaths) > 0, "No valid input files given."

    # Convert background context to int
    if normalizationMethod == "Singlenuc/Dinuc":
        normalizationMethodNum = 1
    elif normalizationMethod == "Trinuc/Quadrunuc":
        normalizationMethodNum = 3
    elif normalizationMethod == "Pentanuc/Hexanuc":
        normalizationMethodNum = 5
    elif normalizationMethod in ("No Normalization", "Custom Background"):
        normalizationMethodNum = None
    else: raise ValueError("Matching strings is hard.")

    # Set the linker offset
    if includeLinker: linkerOffset = 30
    else: linkerOffset = 0

    ### Ensure that every mutation file has a context sufficient for the requested background.

    # create a new list of mutation file paths, replacing any with contexts that are too low.
    if normalizationMethodNum is not None:
        print("\nExpanding file context where necessary...\n")
        updatedMutationFilePaths = list()
        for mutationFilePath in mutationFilePaths:
            mutationFileContext = getContext(mutationFilePath, True)

            # Some error checking...
            assert mutationFileContext is not None, "Malformed file name.  Context is not clear for " + os.path.basename(mutationFilePath)
            assert mutationFileContext != 0, "Mixed context files cannot be normalized by sequence context."
            assert mutationFileContext != -1, "Wait, what?  How did you even get this context for this input file? " + os.path.basename

            if mutationFileContext < normalizationMethodNum:
                updatedMutationFilePaths += expandContext((mutationFilePath,),normalizationMethodNum)
            else: updatedMutationFilePaths.append(mutationFilePath)
    else: updatedMutationFilePaths = mutationFilePaths

    ### Run the rest of the analysis.

    print("\nCounting mutations at each dyad position...")
    nucleosomeMutationCountsFilePaths = countNucleosomePositionMutations(updatedMutationFilePaths, nucleosomeMapNames,
                                                                         useSingleNucRadius, useNucGroupRadius, linkerOffset)

    if normalizationMethodNum is not None:

        print("\nGenerating genome-wide mutation background...")
        mutationBackgroundFilePaths = generateMutationBackground(updatedMutationFilePaths,normalizationMethodNum)

        print("\nGenerating nucleosome mutation background...")
        nucleosomeMutationBackgroundFilePaths = generateNucleosomeMutationBackground(mutationBackgroundFilePaths, nucleosomeMapNames,
                                                                                     useSingleNucRadius, useNucGroupRadius, linkerOffset)

        print("\nNormalizing counts with nucleosome background data...")
        normalizeCounts(nucleosomeMutationBackgroundFilePaths)

    elif normalizationMethod == "Custom Background":
        print("\nNormalizing counts using custom background data...")
        normalizeCounts(list(), nucleosomeMutationCountsFilePaths, customBackgroundDir)


def parseArgs(args):
    
    # If only the subcommand was given, run the UI.
    if len(sys.argv) == 2: 
        main(); return

    # Get the bed mutation files from the given paths, searching directories if necessary.
    finalBedMutationPaths = list()
    assert args.mutation_file_paths is not None, "No mutation file paths were given."
    for mutationFilePath in args.mutation_file_paths:
        if os.path.isdir(mutationFilePath):
            finalBedMutationPaths += [os.path.abspath(filePath) for filePath in getFilesInDirectory(mutationFilePath, DataTypeStr.mutations + ".bed")]
        else: finalBedMutationPaths.append(os.path.abspath(mutationFilePath))

    assert len(finalBedMutationPaths) > 0, "No bed mutation files were found."

    nucleosomeMapNames = list()
    assert args.nucleosome_maps is not None, "No nucleosome maps were given."
    for nucleosomeMapPath in args.nucleosome_maps:
        if os.path.isdir(nucleosomeMapPath): nucleosomeMapNames.append(os.path.basename(nucleosomeMapPath))
        else: nucleosomeMapNames.append(getIsolatedParentDir(os.path.abspath(nucleosomeMapPath)))

    assert len(nucleosomeMapNames) > 0, "No nucleosome maps were found."

    # Determine what normalization method was selected.
    normalizationMethod = "No Normalization"
    customBackgroundDir = None
    if args.context_normalization == 1 or args.context_normalization == 2: normalizationMethod = "Singlenuc/Dinuc"
    elif args.context_normalization == 3 or args.context_normalization == 4: normalizationMethod = "Trinuc/Quadrunuc"
    elif args.context_normalization == 5 or args.context_normalization == 6: normalizationMethod = "Pentanuc/Hexanuc"
    elif args.background is not None: 
        normalizationMethod = "Custom Background"
        if os.path.isdir(args.background): customBackgroundDir = os.path.abspath(args.background)
        else: customBackgroundDir = os.path.dirname(os.path.abspath(args.background))
        if args.generate_background_immediately:
            generateCustomBackground(customBackgroundDir, nucleosomeMapNames, args.singlenuc_radius, 
                                     args.add_linker, args.nuc_group_radius)
    else: assert not args.generate_background_immediately, "Background generation requested, but no background given."

    runAnalysisSuite(list(set(finalBedMutationPaths)), list(set(nucleosomeMapNames)), normalizationMethod, customBackgroundDir, 
                     args.singlenuc_radius, args.add_linker, args.nuc_group_radius)


def main():

    # Create the Tkinter dialog.
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createMultipleFileSelector("Bed Mutation Files:",0,DataTypeStr.mutations + ".bed",("Bed Files",".bed"))

    dialog.createMultipleFileSelector("Nucleosome Map Files", 1, "nucleosome_map.bed", ("Bed Files", ".bed"))

    normalizationSelector = dialog.createDynamicSelector(2, 0)
    normalizationSelector.initDropdownController("Normalization Method",("No Normalization", "Singlenuc/Dinuc", "Trinuc/Quadrunuc", "Pentanuc/Hexanuc", 
                                                                         "Custom Background"))
    customBackgroundFileSelector = normalizationSelector.initDisplay("Custom Background", "customBackground")
    customBackgroundFileSelector.createFileSelector("Custom Background Directory:", 0, ("Bed Files", ".bed"), directory = True)
    customBackgroundFileSelector.createCheckbox("Generate Background now", 1, 0)
    customBackgroundFileSelector.createLabel("", 2, 0)
    normalizationSelector.initDisplayState()

    selectNucleosomeDyadRadius = dialog.createDynamicSelector(3,0)
    selectNucleosomeDyadRadius.initCheckboxController("Run analysis with a single nucleosome dyad radius (73 bp)")
    linkerSelectionDialog = selectNucleosomeDyadRadius.initDisplay(1, "singleNuc")
    linkerSelectionDialog.createCheckbox("Include 30 bp linker DNA on either side of single nucleosome dyad radius.",0,0)
    selectNucleosomeDyadRadius.initDisplayState()

    dialog.createCheckbox("Count with a nucleosome group radius (1000 bp)", 4, 0)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    # Get the user's input from the dialog.
    selections: Selections = dialog.selections
    mutationFilePaths = selections.getFilePathGroups()[0] # A list of paths to bed mutation files
    nucleosomeMapNames = [getIsolatedParentDir(nucleosomeMapFile) for nucleosomeMapFile in selections.getFilePathGroups()[1]]

    normalizationMethod = normalizationSelector.getControllerVar() # The normalization method to be used.
    if normalizationMethod == "Custom Background":
        customBackgroundDir = selections.getFilePaths("customBackground")[0] # Where to find raw counts files to use as custom background
        generateCustomBackgroundNow = selections.getToggleStates("customBackground")[0] # Whether or not to generate the custom background counts on the fly
    else: 
        customBackgroundDir = None
        generateCustomBackgroundNow = False

    useSingleNucRadius = selectNucleosomeDyadRadius.getControllerVar() # Whether or not to generate data with a 73 bp single nuc dyad radius
    if useSingleNucRadius: 
        includeLinker = selections.getToggleStates("singleNuc")[0] # Whether or not to include 30 bp linker DNA in nucleosome dyad positions
    else: includeLinker = False
    useNucGroupRadius = selections.getToggleStates()[0] # Whether or not to generate data with a 1000 bp nuc group dyad radius

    # If requested, generate the background counts file(s).
    if generateCustomBackgroundNow:
        generateCustomBackground(customBackgroundDir, nucleosomeMapNames, useSingleNucRadius,
                                 includeLinker, useNucGroupRadius)

    runAnalysisSuite(mutationFilePaths, nucleosomeMapNames, normalizationMethod, customBackgroundDir, useSingleNucRadius, 
                     includeLinker, useNucGroupRadius)


if __name__ == "__main__": main()