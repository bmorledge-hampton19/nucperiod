# This script takes data from the Kucab et al. mutation compendium paper and converts it to
# a trinucleotide context bed file.
from TkinterDialog import TkinterDialog, Selections
from UsefulBioinformaticsFunctions import reverseCompliment, isPurine
from UsefulFileSystemFunctions import getIsolatedParentDir
import os, subprocess

def parseKucabCompendium(kucabSubstitutionsFilePaths,includeAllPAHs):

    for kucabSubstitutionsFilePath in kucabSubstitutionsFilePaths:

        print("\nWorking in:",os.path.basename(kucabSubstitutionsFilePath))

        if not kucabSubstitutionsFilePath.endswith("final.txt"):
            raise ValueError("Error:  Expected input file from Kucab data which should end in \"final.txt\".")

        # Prepare the output file path.
        localRootDirectory = os.path.dirname(kucabSubstitutionsFilePath)
        dataGroupName = getIsolatedParentDir(kucabSubstitutionsFilePath)
        if includeAllPAHs: dataGroupName += "_all_PAHs"
        else: dataGroupName += "_smoker_lung"
        outputTrinucBedFilePath = os.path.join(localRootDirectory,dataGroupName+"_trinuc_context.bed")

        # These are the designations for PAH mutation signatures, the ones related to tobacco smoke that we want to study.
        PAHDesignations = ("MSM0.54","MSM0.26","MSM0.92","MSM0.2","MSM0.42","MSM0.74","MSM0.103"
                           "MSM0.14","MSM0.82","MSM0.130","MSM0.12","MSM0.132","MSM0.13","MSM0.96")
        # These designations specifically mimic the indel signature in smokers' lung cancer tumors.
        LungCancerSpecificDesignations = ("MSM0.26","MSM0.92","MSM0.2","MSM0.103","MSM0.14")

        # Set the designations that will be used to collect data based on the input to the function.
        if includeAllPAHs:
            relevantDesignations = PAHDesignations
        else: relevantDesignations = LungCancerSpecificDesignations

        print("Reading data and writing to trinuc bed file...")
        with open(kucabSubstitutionsFilePath, 'r') as kucabSubstitutionsFile:
            with open(outputTrinucBedFilePath, 'w') as outputTrinucBedFile:

                firstLineFlag = True
                for line in kucabSubstitutionsFile:
                    
                    # Skip the first line with headers.
                    if firstLineFlag:
                        firstLineFlag = False
                        continue

                    # The lines are separated by tabs.  The relevant data have the following indices in a tab-separated list:
                    # 15: mutagen designation
                    # 4: Chromosome
                    # 5: Start Pos (1 base)
                    # 6: Reference base
                    # 7: Mutated base
                    # 13: pre-base context
                    # 14: post-base context
                    choppedUpLine = line.strip().split('\t')

                    # Skip the mutation if it does not belong to the relevant group.
                    if not choppedUpLine[15] in relevantDesignations: continue

                    # Compile the necessary information for the bed file.
                    chromosome = "chr" + choppedUpLine[4]
                    startPos1Base = choppedUpLine[5]
                    startPos0Base = str(int(startPos1Base)-1)

                    mutatedFrom = choppedUpLine[6]
                    mutatedTo = choppedUpLine[7]
                    trinucContext = ''.join((choppedUpLine[13],mutatedFrom,choppedUpLine[14]))

                    # If the mutated base is listed as arising from a purine, flip the mutation and the strand.
                    if isPurine(mutatedFrom):
                        mutation = reverseCompliment(mutatedFrom) + '>' + reverseCompliment(mutatedTo)
                        strand = '-'
                        trinucContext = reverseCompliment(trinucContext)
                    else:
                        mutation = mutatedFrom + '>' + mutatedTo
                        strand = '+'

                    # Write the information to the trinuc bed file.
                    outputTrinucBedFile.write('\t'.join((chromosome, startPos0Base, startPos1Base,
                                                         trinucContext, mutation, strand)) + '\n')

        # Sort the output file.
        print("Sorting output file...")
        subprocess.run(" ".join(("sort","-k1,1","-k2,2n",outputTrinucBedFilePath,"-o",outputTrinucBedFilePath)),
                           shell = True, check = True)


if __name__ == "__main__":

    #Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=os.path.join(os.path.dirname(__file__),"..","data"))
    dialog.createMultipleFileSelector("Kucab Substitutions File Paths:",0,"final.txt",("text files",".txt")) #NOTE: Weird file ending?
    dialog.createCheckbox("Include all PAH Designations",1,0)
    dialog.createReturnButton(2,0)
    dialog.createQuitButton(2,2)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    # Get the user's input from the dialog.
    selections: Selections = dialog.selections
    kucabSubstitutionsFilePaths = list(selections.getFilePathGroups())[0]
    includeAllPAHs = list(selections.getToggleStates())[0]

    parseKucabCompendium(kucabSubstitutionsFilePaths, includeAllPAHs)