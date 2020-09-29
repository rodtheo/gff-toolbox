## Def filter help
usage_filter="""
gff-toolbox:

            Filter

This command uses Biopython library to parse and filter your GFF file as you wish. It targets the
attributes column of the GFF.

usage:
    gff-toolbox filter [-h|--help ]
    gff-toolbox filter [ --mode loose ] [ --input <gff> ] [ --pattern <string> --column <int> --sort --header ]
    gff-toolbox filter [ --mode exact ] [ --input <gff> ] [ --chr <chr_limits> --source <source_limits> --type <type_limits> --start=<start_position> --end=<end_position> --strand=<strand> ]

options:

                                                Generic parameters

    -h --help                                               Show this screen.

    -i, --input=<gff>                                       Input GFF file. GFF file must not contain sequences, only features.

    -m, --mode=<search_mode>                                In which mode to search for patterns: loose or exact? In loose mode,
                                                            the GFF is scanned in a grep-like manner via pandas dataframes in which
                                                            user must specify a pattern and a column to do the search. This mode is
                                                            recommended for simple searches with simple GFFs (not nested). The exact
                                                            mode scans the GFF with Biopython and BCBio packages, treating it as
                                                            python dictionary. It is recommended for more complex searches and complex
                                                            GFFs, such as nested GFFs. [Default: exact]

                                                Loose search mode parameters

    -c, --column=<int>                                      Apply pattern search in which GFF columns? [Default: 9]

    -p, --pattern=<string>                                  Pattern to search in the GFF file. Can be a list of patterns separated by commas.

    --sort                                                  Sort the GFF by the contig and start position.

    --header                                                Print GFF header (##gff-version 3)? Some programs require this header.

                                                Exact search mode parameters

    --chr=<chr_limits>                                      Apply a filter based on the chr/contig/sequence ids (Column 1). Can be a list of patterns separated by commas.
                                                            This step only works using the complete string for full-matches (it does not work with partial-matches based
                                                            subsetrings of the desired pattern).

    --source=<source_limits>                                Apply a filter based on the source column (Column 2). Can be a list of patterns separated by commas.
                                                            This step works using the complete string (with full-matches) or substrings of the desired pattern,
                                                            working with partial-matches.

    --type=<type_limits>                                    Apply a filter based on the type column (Column 3). Can be a list of patterns separated by commas.
                                                            This step works using the complete string (with full-matches) or substrings of the desired pattern,
                                                            working with partial-matches.

    --strand=<strand>                                       Apply a filter based on the strand of the feature. Options: plus or minus. By default, everything is given.

    --start=<start_position>                                Apply a filter to select features starting from this position.

    --end=<end_position>                                    Apply a filter to select features until this position.


example:

    ## Simple filter in any column: wheter a line contain a pattern in a specific column (like grep)

$ gff-toolbox filter --mode loose --sort --header -i test/input.gff -c 2 -p "barrnap:0.9"

    ## In the example below, we filter the GFF in a complex manner:
    ## All the features found in the sequences named contig_6_segment0 and contig_7_segment0 that
    ## have CARD and/or Prodigal in their second column (sources) and are classified as CDS.

$ gff-toolbox filter -i test/input.gff --chr contig_6_segment0,contig_7_segment0 --source CARD,Prodigal --type CDS
"""

##################################
### Loading Necessary Packages ###
##################################
import sys
import pandas as pd
import re
from BCBio import GFF
from BCBio.GFF import GFFExaminer
import subprocess

####################################
### Function to import gff as df ###
####################################
def read_gff_df(input):
    return pd.read_csv(input, sep = "\t", comment = "#",
                        names=['1', '2', '3', '4', '5', '6', '7', '8', '9'])

# Guide: ['Chr', 'Source', 'Type', 'Start', 'End', 'Score', 'Strand', 'Phase', 'Attributes'

######################################
### Function to import gff as dict ###
######################################
def read_gff_dict(input, chr_limits, source_limits, type_limits, strand, start_pos, end_pos):

    # Check for the limits imposed by the user
    limit_info = {}

    # Chr limit?
    if chr_limits != None:
        chr_list = list(chr_limits.split(','))
        limit_info['gff_id'] = chr_list

    # Customisable limits
    ## Module
    examiner = GFFExaminer()

    ## Open connections
    summary = examiner.available_limits(open(input))
    gff_sources = []
    gff_types = []

    ## Get sources
    for keys in summary['gff_source'].keys():
        key = str(keys).replace("('", "").replace("',)", "")
        gff_sources.append(key)

    ## Get types
    for keys in summary['gff_type'].keys():
        key = str(keys).replace("('", "").replace("',)", "")
        gff_types.append(key)

    # Source limits?
    if source_limits != None:
        src_definitive  = [] # The real patterns in the GFF
        src_list = list(source_limits.split(',')) # Patterns given by user
        for source in gff_sources:
            if bool(re.search('|'.join(src_list), str(source))): # Check wheter the pattern given by user is present in the GFF
                src_definitive.append(str(source)) # Select the real pattern that have the pattern given by user, for biopython dict

            limit_info['gff_source'] = list(set(src_definitive))

    # Type limits?
    if type_limits != None:
        type_definitive = [] # The real patterns in the GFF
        type_list = list(type_limits.split(',')) # Patterns given by user
        for type in gff_types:
            if bool(re.search('|'.join(type_list), str(type))): # Check wheter the pattern given by user is present in the GFF
                type_definitive.append(str(type)) # Select the real pattern that have the pattern given by user, for biopython dict

        limit_info['gff_type'] = list(set(type_definitive))

    # Open GFF
    for rec in GFF.parse(open(input), limit_info=limit_info):

        indexes = [] # Indexes to remove

        # Remove features based on strand
        ## Wants plus strand
        if strand == "plus":
            for index, f in enumerate(rec.features):
                if int(f.location.strand) == -1:
                    indexes.append(int(index))

        ## Wants minus strand
        if strand == "minus":
            for index, f in enumerate(rec.features):
                if int(f.location.strand) == 1:
                    indexes.append(int(index))

        # Remove features based on position
        ## Min (start)
        if start_pos != None:
            for index, f in enumerate(rec.features):
                if int(f.location.start) + 1 < int(start_pos): # Biopython is zero-based
                    indexes.append(int(index))

        ## Max (end)
        if end_pos != None:
            for index, f in enumerate(rec.features):
                if int(f.location.end) > int(end_pos):
                    indexes.append(int(index))

        # Remove unwanted features
        rec.features = [i for j, i in enumerate(rec.features) if j not in list(set(indexes))]

    # Done
    return rec


###################################
### Filter df by column pattern ###
###################################
def df_col_filter(df, column, pattern):

    # Split csv
    pat_list = list(pattern.split(','))

    # Filter
    return df[
        df[str(column)].str.contains('|'.join(pat_list))
    ].to_csv(sep='\t', index=False, header=False).strip()

######################################################
### Function for simple filter with single pattern ###
######################################################
def filter_loose_mode(input_gff, column, pattern, sort, header):

    # Read GFF file
    df = read_gff_df(input_gff)

    # Sort
    if sort == True:
        df = df.sort_values(by=['1', '4'])

    # header
    if header == True:
        print("##gff-version 3")

    # Filter
    print(df_col_filter(df=df, column=str(column), pattern=str(pattern)))

#######################################################
### Function for complex filter with single pattern ###
#######################################################
def filter_exact_mode(input_gff, chr_limits, source_limits, type_limits, start_pos, end_pos, strand):

    # Parse fields
    gff_dict = read_gff_dict(input=input_gff, chr_limits=chr_limits, source_limits=source_limits, type_limits=type_limits,
                             strand=strand, start_pos=start_pos, end_pos=end_pos)

    # Print
    GFF.write([gff_dict], sys.stdout) # Write filtered gff

################
### Def main ###
################
def filter(input_gff, column, pattern, sort, header, mode, chr_limits, source_limits, type_limits, start_pos, end_pos, strand):

    # Simple filter
    if mode == "loose":
        filter_loose_mode(input_gff=input_gff, column=column, pattern=pattern, sort=sort, header=header)

    # Complex filter
    elif mode == "exact":
        filter_exact_mode(input_gff=input_gff, chr_limits=chr_limits, source_limits=source_limits, type_limits=type_limits,
                          start_pos=start_pos, end_pos=end_pos, strand=strand)

    # Error
    else:
        print(f"""
Error: --mode must be either 'loose' or 'exact'. {mode} is incorrect.
        """)
