''' db analyzer '''

# Make sure messagearchive.db and rgb.csv are in the same directory as
# this program before running.

print('Importing libraries...')
import time
starttime = time.time()
import sqlite3
import re
import shutil
import sys
import csv
import hashlib
import datetime
import os
import colorsys
import math
import matplotlib.pyplot as plt
from random import randint

# Verify that the necessary files are in place
cwd = os.getcwd()
scd = os.path.dirname(os.path.realpath(__file__))
scn = os.path.basename(__file__)
fc = 0
if cwd != scd:
    print('ERROR: current working directory is')
    print('  '+cwd)
    print('while '+ scn +' was saved in')
    print('  '+scd)
    print('Please "cd" into the same folder this script was saved in, '
        'then rerun.')
    sys.exit(0)
if not os.path.exists('messagearchive.db'):
    fc = 1
    print('ERROR: Cannot find messagearchive.db')
if not os.path.exists('rgb.csv'):
    fc = 1
    print('ERROR: Cannot find rgb.csv')
if fc != 0:
    print('Add the above file(s) to the same directory as this script,')
    print('  '+scd+',')
    print('then rerun.')
    sys.exit(0)


# Regular expression search function for use in the sqlite3 engine.
def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None

# Simple SHA256 hash function.  Text goes in hash comes out.
def sha256hashfunction(texttohash):
    textbytes = bytes(texttohash, 'utf-8')
    hash_object = hashlib.sha256(textbytes)
    return hash_object.hexdigest()

# Grabs names from the database and hashes them using the above
# function.  The input text is the hash salt (defined in the global
# variable declaration) plus the username.
def hashusernames():
    cur.execute('SELECT author FROM messages ORDER BY author')
    prehash0 = cur.fetchall()
    prehash = [itemx[0] for itemx in prehash0]
    posthash = [sha256hashfunction(hashsalt+str(phitem)) for phitem in prehash]
    return posthash

# Grabs UNIX aka EPOCH time strings from the database and converts them
# into human readable dates (UTC timezone). Time (hh:mm:ss) is not
# generated to protect privacy.
def getdates():
    cur.execute('SELECT created FROM messages ORDER BY created')
    unixtime0 = cur.fetchall()
    unixtime = [itemd[0] for itemd in unixtime0]
    readabletime = [
    datetime.datetime.utcfromtimestamp(int(itemd0)).strftime('%Y-%m-%d')
    for itemd0 in unixtime
    ]
    return readabletime


''' Database Initialization & Global Variable Declaration '''
# Get the current time/date in ISO 8601 format.
timevar = time.strftime('%Y%m%dT%H%M%S')

# Tell the file utility where our main database is.
cwd = os.getcwd()+'\\'
srcdbname = 'messagearchive.db'
srcdbpath = cwd + srcdbname

# Tell the file utility where we want our working copy.
xportdir = cwd + timevar + '\\'
if not os.path.exists(xportdir):
    os.makedirs(xportdir)
destdbname = 'messagearchive-analyzed-'+timevar+'.db'
destdbpath = xportdir + destdbname

# Make a copy of the db so we don't irreversibly mess something up.
shutil.copy2(srcdbpath, destdbpath)

# Connect to our safe working copy.
sql = sqlite3.connect(destdbpath)
sql.create_function('REGEXP', 2, regexp)
cur = sql.cursor()

print('Copied database over to '+destdbname)

hashsalt = 'usernamehash+/u/'

def main():
    # Add another table alongside 'messages' called 'ColorsToSearch.'
    # This table will store every possible color we'll search for.
    # http://www.sqlitetutorial.net/
    cur.execute(
        'CREATE TABLE ColorsToSearch (                                        \
        Cindex INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,             \
        Color TEXT NOT NULL UNIQUE,                                           \
        ColorHex TEXT,                                                        \
        ColorCount INTEGER DEFAULT 0                                          \
        );'
    )

    # Import rgb.csv, aka our list of known colors.
    with open('rgb.csv','rt') as fin:
        dr = csv.DictReader(fin)
        to_db = [(i['Color'], i['ColorHex']) for i in dr]

    # Put the contents of to_db (rgb.csv) into the database.
    cur.executemany(
        'INSERT INTO ColorsToSearch                                           \
        (Color, ColorHex)                                                     \
        VALUES (?, ?);',
        to_db
    )
    sql.commit()

    # Find the number of colors we just added - we'll use that as the
    # length of the for loop.
    cur.execute('SELECT COUNT(*) FROM ColorsToSearch')

    # Store the only row returned from the select statement.
    # fetchone() returns a list, but since there's only one item in the
    # list we add a [0] to turn it into a regular variable.
    locolorstosearch = cur.fetchone()[0]
    print(str(locolorstosearch)+' search terms imported from rgb.csv')

    # Find the total number of messages we have to search.  This number
    # isn't critical for any calculations, it's only used to display
    # info in the command shell.
    cur.execute('SELECT COUNT(*) FROM messages')
    numberofmessages = cur.fetchone()[0]

    # Add a new column that will hold all the color tags our program
    # finds for each message. The tag column is capable of holding
    # muliple tags per message, as the sql UPDATE appends new tags.
    cur.execute('ALTER TABLE messages ADD COLUMN tag TEXT;')
    cur.execute('UPDATE messages SET tag = (?)',('',))
    sql.commit()

    print('Converting UNIX timestamps to readable format...')
    # Call the getdates() function and return a list of human-readable
    # dates from the database's timestamps.
    utcdates = getdates()
    cur.execute('ALTER TABLE messages ADD COLUMN UTCdate TEXT;')
    # It's important that this next statement's ORDER BY is the same as
    # the ORDER BY in getdates()
    cur.execute('SELECT created FROM messages ORDER BY created')
    # Grab the contents of the last select statement and iterate over
    # each row. unixtindex and utcdates should both be the same length,
    # as they both contain date representations of every message.
    unixtindex=[row[0] for row in cur]
    for k,b in zip(utcdates,unixtindex):
        cur.execute(
            'UPDATE messages SET UTCdate = (?) WHERE created = (?)',
            (k,b)
        )
    sql.commit()

    # Very similar to the previous block of code.
    # See above for further comments.
    print('Generating SHA-256 user hashes with prefix salt '+ hashsalt +'...')
    hashed = hashusernames()
    cur.execute('ALTER TABLE messages ADD COLUMN hash TEXT;')
    cur.execute('SELECT author from messages ORDER BY author')
    hcindex=[row[0] for row in cur]
    for j,c in zip(hashed,hcindex):
        cur.execute(
            'UPDATE messages SET hash = (?) WHERE author = (?)',
            (j,c)
        )
    sql.commit()

    # Begin iterating over each color in 'ColorsToSearch.'  In each
    # cycle of the loop, the engine searches every message in the
    # database against only one color.
    count = 0
    while count < locolorstosearch:
        count += 1
        # Determine the color of interest for this go around.
        cur.execute(
            'SELECT Color FROM ColorsToSearch                                 \
            WHERE Cindex = (?) GROUP BY Color',
            (count,)
        )
        searchcolor = cur.fetchone()[0]
        searchcolortag = str('<') + searchcolor + str('>')
        # "Slash b" means word boundary in Regex.  This prevents words
        # like 'cared' from being tagged as red.
        searchcolorregexp = '\\b'+searchcolor+'\\b'
        # Append the current search color's tag to the tag column if
        # there's a match.  To make regexp case-insensitive we force
        # each side of the query logic to use lowecase.
        cur.execute(
            'UPDATE messages                                                  \
            SET tag = tag || (?)                                              \
            WHERE tag IS NOT NULL                                             \
            AND                                                               \
            (                                                                 \
                LOWER(Subject) REGEXP LOWER(?)                                \
                OR                                                            \
                LOWER(Body) REGEXP LOWER(?)                                   \
            )',
            (searchcolortag,searchcolorregexp,searchcolorregexp,)
        )
        # Sum up all the matches we just made for use in our report
        # later on.
        cur.execute(
            'SELECT COUNT(*) FROM messages                                    \
            WHERE tag LIKE (?)',
            ('%'+searchcolortag+'%',)
        )
        numberofmessagestagged = cur.fetchone()[0]
        # Update our current color of interest's entry in the
        # colorstosearch table with the number of regex hits we just
        # found of it in messages.
        cur.execute(
            'UPDATE ColorsToSearch                                            \
            SET ColorCount = ?                                                \
            WHERE Color = ?',
            (numberofmessagestagged,searchcolor,)
        )
        # Progress bar
        print(str(round(100*count/locolorstosearch,1))+'% done. '
            '('+str(numberofmessagestagged)+') '+searchcolor +
            ' was found in ' + str(numberofmessagestagged) + ' out of ' +
            str(numberofmessages) + ' messages')

    if extrasearch == 1:
        # Hexsearch() calls are ordered most important to least.
        # Hexsearch only searches for untagged messages. If an entry
        # would match more than one of these regex patters, its tag
        # will still only show the first pattern matched.  This area is
        # for tags that should only be applied as a last resort, and
        # also for tags where the regex search is defined differently
        # than the tag.
        hexsearch('hex defined color','<hexcolorT1>','','#[0-9A-Fa-f]{2}',)
        ParseColorHexCode()
        hexsearch('pantone','<pantone>','','\\bpantone\\b',)
        hexsearch('toaster struddle','<toast>','',r'\btoast(er)?\b')
        hexsearch('colorblind','<blind>','',r'\b(colou?r)?blind\b')
        hexsearch('hex defined colorNO#','<hexcolorT2>','',r'\b[0-9A-Fa-f]{6}\b',)
        ParseColorHexCodeNOHT()
        # Unknown URL must be last.  Many messages included links to
        # the post auto-included by RES, which we don't want to
        # capture if another hexsearch is more relevant.
        hexsearch('unknown url','<URL>','','http',)

    # Cleaning up the colorstosearch table
    cur.execute(
        'UPDATE ColorsToSearch SET ColorHex = ? WHERE ColorHex IS NULL',
        ('',)
    )

    # Count the number of messages we didn't match with a color.
    cur.execute('SELECT COUNT(*) FROM messages WHERE tag = ?',('',))
    untagged = cur.fetchone()[0]
    print(str(untagged) + ' unknown, untagged messages remaining')
    sql.commit()

# Export a csv that includes all identified colors, their respective
# hex value (for use in properly shading the visualization) and how
# many messages included each color.
def exportreportcsv():
    report_count_filename = 'report_count_' + timevar + '.csv'
    print('Generating totals report ('+ report_count_filename +')...')
    cur.execute(
        'SELECT color, colorhex, colorcount                                   \
        FROM ColorsToSearch                                                   \
        WHERE colorcount != 0                                                 \
        ORDER BY colorcount DESC'
    )
    reportcsv = cur.fetchall()
    with open((xportdir + report_count_filename),'w') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['color', 'colorhex', 'colorcount'])
        writer.writerows(reportcsv)


# Export a csv that includes a bit of data from each message. This data
# includes a (poorly) salted SHA-256 hash of the username, each color
# identified in their message, and the GMT/UTC date the message was
# sent. Full timestamp, unhashed username, message body, and message
# text are not included to protect privacy, as this data will be
# publicly available for users to chack and see what the script got
# from their message.
def exportgdocscsv():
    report_gdocs_filename = 'report_gdocs_' + timevar + '.csv'
    print('Generating username hash lookup table ('
        + report_gdocs_filename +')...')
    cur.execute(
        'SELECT hash, utcdate, tag                                            \
        FROM messages                                                         \
        ORDER BY hash DESC'
    )
    reportgdocscsv = cur.fetchall()
    with open((xportdir + report_gdocs_filename),'w') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['hash', 'utcdate', 'tag'])
        writer.writerows(reportgdocscsv)

# Additional regex search for tags that aren't in rgb.csv.  Useful for
# tags that have different values for their true name, tag value, and
# regex search. E.g. "blue <blue> \bblue\b" versus
# "hex defined color <hexcolorT1> #[0-9A-Fa-f]{2}"
def hexsearch(hexsN,hexsA,hexsB,hexsC,):
    print('Searching with regex '+hexsC+' and tagging as '+hexsA)
    cur.execute(
        'UPDATE messages                                                      \
        SET tag = tag || (?)                                                  \
        WHERE tag = (?)                                                       \
        AND                                                                   \
        (                                                                     \
            LOWER(Subject) REGEXP LOWER(?)                                    \
            OR                                                                \
            LOWER(Body) REGEXP LOWER(?)                                       \
        );',
        (hexsA,hexsB,hexsC,hexsC,)
    )
    sql.commit()
    cur.execute(
        'SELECT COUNT(*) FROM messages WHERE tag LIKE (?)',
        ('%'+hexsA+'%',)
    )
    customtagcount = cur.fetchone()[0]
    print('  '+str(customtagcount)+' found')
    cur.execute(
        'INSERT INTO ColorsToSearch (Color,ColorCount) VALUES(?, ?)',
        (hexsN,customtagcount,)
    )
    sql.commit()

# Function that parses each hex value from colorstosearch and assigns
# each entry a new column for red, green, blue, hue, saturation, and
# value.  Each of these is on a scale of 0 to 1.
def splitrgb():
    # Grab all of our color hex values.
    cur.execute(
        'SELECT colorhex                                                      \
        FROM ColorsToSearch                                                   \
        WHERE colorcount != ?                                                 \
        AND colorhex != ?                                                     \
        ORDER BY ColorHex DESC',
        (0,'',)
    )
    rgbhex0 = cur.fetchall()
    rgbhex = [itemr[0] for itemr in rgbhex0]
    # Split the hex into its red, green, and blue components.
    rhex = [int(itemrx[1:3], 16)/255 for itemrx in rgbhex]
    ghex = [int(itemgx[3:5], 16)/255 for itemgx in rgbhex]
    bhex = [int(itembx[5:7], 16)/255 for itembx in rgbhex]
    # Use colorsys to translate the RGB to HSV.  Hue allows for a more
    # logical way to arrange the data.
    hsv = [colorsys.rgb_to_hsv(rhex[i], ghex[i], bhex[i])
        for i in range(0,len(rhex))]
    hhsv = [itemh[0] for itemh in hsv]
    shsv = [itemh[1] for itemh in hsv]
    vhsv = [itemh[2] for itemh in hsv]
    # Select the rest of the data to include the count and name in the
    # report.
    cur.execute(
        'SELECT color, colorhex, colorcount                                   \
        FROM ColorsToSearch                                                   \
        WHERE colorcount != ?                                                 \
        AND colorhex != ?                                                     \
        ORDER BY ColorHex DESC',
        (0,'',)
    )
    colortosearchsql = cur.fetchall()
    sqlcolor = [i[0] for i in colortosearchsql]
    sqlhex = [str(i[1]) for i in colortosearchsql]
    sqlcount = [i[2] for i in colortosearchsql]

    # Make a report table logging all of what we just did.
    print('Updating database with RGB/HSV components..')
    cur.execute(
        'CREATE TABLE Report (                                                \
            OIndex INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,         \
            Colorname TEXT NOT NULL UNIQUE,                                   \
            Hex TEXT,                                                         \
            HexVerify TEXT,                                                   \
            Red TEXT,                                                         \
            Green TEXT,                                                       \
            Blue TEXT,                                                        \
            Hue REAL,                                                         \
            Saturation REAL,                                                  \
            Value REAL,                                                       \
            CCount INTEGER NOT NULL                                           \
        )'
    )

    # stackoverflow.com/questions/2092757/
    # Iterate over each color to be added to the report table.  Wish I
    # could get cur.executemany() to work here and avoid the for loop,
    # but every time I tried python would return an error on the wrong
    # number of imput tuples.
    for i in range(len(sqlcolor)):
        cur.execute(
            'INSERT INTO Report                                               \
                (Colorname, Hex, HexVerify, Red, Green, Blue,                 \
                Hue, Saturation, Value, CCount)                               \
            VALUES(?,?,?,?,?,?,?,?,?,?);',
            (sqlcolor[i],sqlhex[i],rgbhex[i],
            rhex[i],ghex[i],bhex[i],hhsv[i],
            shsv[i],vhsv[i],int(sqlcount[i]),)
        )
    sql.commit()

# Draw a bubble graph of each color and export as a png image
def renderHSVchart(SATorVAL,NonRGBorClean,labelsbool,transparency,linewidthIA,filetypeIA):
    # glowingpython.blogspot.com/2011/11/how-to-make-bubble-charts-with.html

    # First input argument determines which HSV element is represented
    # on the Y-axis.  This value must either be 8 for Saturation or 9
    # for Value.  Argument two determines if CountNonRGBtag and
    # CountUntagged are plotted.  1 for yes, plot them. 0 for no, limit
    # the plot to defined colors only.
    plt.cla()
    plt.clf()

    AreaFactor = 4
    HSVchartName = timevar

    if SATorVAL == 8: # Saturation
        HSVchartName += '-HueSat'
        LabelSATorVAL = 'Sat'
    elif SATorVAL == 9: # Value
        HSVchartName += '-HueVal'
        LabelSATorVAL = 'Val'
    else:
        print('Error:Undefined Y axis')
        sys.exit(0)

    # Grab everything we have both a tag and RGB hex for.
    # Regardless of RGBonly or both, this needs to be done.
    cur.execute('SELECT * FROM Report ORDER BY CCount ASC')
    rdata = cur.fetchall()

    if labelsbool == 0:
        HSVchartName += '-labelsOFF'
    else:
        HSVchartName += '-labelsON'

    Tstr = str(transparency)
    # Remove the dot from the filename
    # https://stackoverflow.com/a/3939381
    HSVchartName += '-T'+re.sub(r'\.','',Tstr)
    HSVchartName += '-LW'+str(linewidthIA)

    if NonRGBorClean == 0: # RGBonly
        axisXMIN = -0.15
        HSVchartName += '-clean'
    else: # Non RGB tags too
        axisXMIN = -0.35
        HSVchartName += '-nonrgb'
        # Grab the tags without an RGB hex.
        cur.execute('SELECT SUM(ColorCount) FROM ColorsToSearch               \
            WHERE ColorHex = ?', ('',))
        CountNonRGBtag = cur.fetchone()[0]

        # Grab everything else that doesn't have a tag.
        cur.execute('SELECT COUNT(*) FROM messages WHERE tag = ?',('',))
        CountUntagged = cur.fetchone()[0]

        # Non-RGB tags
        qx = -.2
        qy = .65
        qcolor = '#ffffff'
        qarea = AreaFactor*CountNonRGBtag
        # Unknown and untagged
        zx = -.2
        zy = .35
        zcolor = '#ffffff'
        zarea = AreaFactor*CountUntagged

        sct2 = plt.scatter(qx, qy, c=qcolor, s=qarea, linewidths=linewidthIA,
            edgecolor='black', hatch='.') # Closed dot for tagged non RGB
        sct3 = plt.scatter(zx, zy, c=qcolor, s=zarea, linewidths=linewidthIA,
            edgecolor='black', hatch='o') # Open dot for unknown untagged
        sct2.set_alpha(.7)
        sct3.set_alpha(.7)

        if labelsbool != 0:
            AddLabel('Other',qarea,qx,qy,AreaFactor)
            AddLabel('Unknown',zarea,zx,zy,AreaFactor)
            
    if filetypeIA == 0:
        HSVchartName +='.png'
    else:
        HSVchartName +='.svg'

    x = []
    y = []
    color = []
    area = []
    count = 0
    for data in rdata:
        count+=1
        x.append(data[7]) # Hue plotted on the X
        y.append(data[SATorVAL]) # 9=Value, 8=Saturation
        color.append(data[2]) # Color of each point
        area.append(AreaFactor*(data[10])) # Size of each dot
        if labelsbool != 0 and count > (len(rdata)-25):
            # Label the top "N" values with their name and count.  To
            # ensure entries with higher counts overlap the lower
            # counts, the sqlite select statement is ordered by Ccount
            # ascending.  The entry with the Nth highest count is
            # plotted first, so all successive higher counts (through
            # 1st) overlap with the previous.  This ensures 1st always
            # overlaps 2nd and so on.
            AddLabel(str(data[1]),AreaFactor*data[10],data[7],data[SATorVAL],
                AreaFactor)

    # Plot parameters
    sct1 = plt.scatter(x, y, c=color, s=area, linewidths=linewidthIA,
        edgecolor='black',)
    sct1.set_alpha(transparency)

    plt.xlabel('Hue')
    plt.ylabel(LabelSATorVAL)
    plt.axis([axisXMIN,1.15,-.15,1.15])
    if filetypeIA == 1 : plt.axis('off') # Hide axes if SVG
    plt.savefig((xportdir + HSVchartName), bbox_inches='tight', dpi=900)
    print('Exported ' + HSVchartName)
    # Clear the chart in case this function is called again.
    plt.cla()
    plt.clf()

def AddLabel(cName,PointArea,labelX,labelY,aFactor):
    # https://stackoverflow.com/a/5147430
    plt.annotate(
        cName+' - '+str(int(round(PointArea/aFactor))),
        size=5,
        xy=(labelX,labelY), xytext=(-20+randint(-1,1),20+randint(-1,1)),
        textcoords='offset points',
        ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.5),
        arrowprops=dict(arrowstyle = '->', connectionstyle='arc3,rad=0')
    )


# Pie chart displaying the top N non RGB tags found
def RenderPieChart(limitarg):
    # matplotlib.org/examples/pie_and_polar_charts/pie_demo_features
    plt.cla()
    plt.clf()
    PieChartName = 'Top'+str(limitarg)+'NonRGBtags.png'
    PieChartTitle = 'Top '+str(limitarg)+' Non-RGB Tags ("Other" bubble on plot)'
    
    # Only the top N tags are displayed.  We still want a slice to
    # represent the rest, i.e. 'others.'  This statement sums up every
    # non rgb-hex tag.
    cur.execute('SELECT SUM(ColorCount) FROM ColorsToSearch \
        WHERE ColorHex = ?', ('',))
    piecharttotal = cur.fetchone()[0]
    
    # Grab the data we'll use to plot, limited to the top N.
    cur.execute('SELECT Color, ColorCount FROM ColorsToSearch                 \
        WHERE ColorHex = ? AND ColorCount > 1                                 \
        ORDER BY ColorCount DESC LIMIT ?', ('',limitarg,))
    piedata = cur.fetchall()
    labels = [(str(item[0])+' - '+str(item[1])) for item in piedata]
    sizes = [item[1] for item in piedata]
    piechartdisplayed = sum(sizes)
    labels.append('Other - '+str(piecharttotal-piechartdisplayed))
    sizes.append(piecharttotal-piechartdisplayed)

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=20)
    ax1.axis('equal')
    plt.suptitle(PieChartTitle, fontsize=12)
    plt.savefig((xportdir + PieChartName), bbox_inches='tight', dpi=300)
    print('Exported ' + PieChartName)
    plt.cla()
    plt.clf()

# Grab every item tagged as <hexcolorT1> and extract the hex value
# using regular expressions.  Tag each entry with its parsed hex code
# and add that to the colorstosearch table.  Subtract away the number
# of parsed tags from the count of hexcolort1 in the table--the
# remainder represents messages where the parser failed.
def ParseColorHexCode():
    print('Parsing hex values from messages...')
    cur.execute('SELECT created, subject, body, tag, idstr FROM messages      \
        WHERE tag LIKE (?) ORDER BY created DESC',('%<hexcolorT1>%',))
    ColorHexCodeTable = cur.fetchall()
    badcount = 0
    goodcount = 0
    customcount = 0
    for item in ColorHexCodeTable:
        ParsedHex = ''
        # Search subject[1] and body[2] for the regex pattern.
        # re.I = ignorecase, re.M = multiline search
        RegexSearchObj = re.search( r'#([a-f0-9]{6})',
            item[1]+' '+item[2], re.M|re.I)
        if RegexSearchObj: # If that pattern exists,
            # Then grab the text within the parenthesis, group 1.
            ParsedHex = RegexSearchObj.group(1).lower()
        else:
            # Before we abandon this search, first try to find a three
            # character abbreviated match (hex shorthand).
            # http://www.websiteoptimization.com/speed/tweak/hex/
            RegexSearchObj3CHAR = re.search( r'#([a-z0-9]{3})',
                item[1]+' '+item[2], re.M|re.I)
            if RegexSearchObj3CHAR:
                ParsedHex = RegexSearchObj3CHAR.group(1).lower()
                # Expand the 3 character code into standard 6
                ParsedHex = (ParsedHex[0] + ParsedHex[0]
                            +ParsedHex[1] + ParsedHex[1]
                            +ParsedHex[2] + ParsedHex[2])
            else:
                badcount += 1
                ParsedHex = 'badhex'
        if ParsedHex != 'badhex':
            goodcount += 1
        # Add the hex we parsed as a secondary tag for that entry
        cur.execute('UPDATE messages SET tag = tag || (?)                     \
            WHERE created LIKE (?) AND idstr LIKE (?)',
            ('<'+ParsedHex+'>','%'+str(item[0])+'%','%'+str(item[4])+'%'))
        cur.execute('SELECT COUNT(*) FROM ColorsToSearch                      \
        WHERE LOWER(ColorHex) LIKE LOWER(?);',('%#'+ParsedHex+'%',))
        colorexistsbool = cur.fetchone()[0]
        if colorexistsbool == 0:
            # If this is a new custom hex, add a new entry into the
            # colorstosearch summary table.
            customcount += 1
            cur.execute('INSERT INTO ColorsToSearch                           \
                (Color, ColorHex, ColorCount) VALUES(?,?,?)',
                ('customhex'+str(customcount)+'-'+ParsedHex,'#'+ParsedHex,1))
        else:
            # If this hex already exists as an entry in the table, add
            # 1 to that count.  This accounts for both colors that
            # line up exactly with rgb.csv and multiple submissions of
            # the same custom hex.
            cur.execute('UPDATE ColorsToSearch SET ColorCount = ColorCount + 1\
                WHERE LOWER(ColorHex) LIKE LOWER(?);',('%#'+ParsedHex+'%',))

    if badcount != 0:
        print('!!!!!WARNING: Hex Parser failed on '+str(badcount)
            +' message(s)!!!!!')

    cur.execute('SELECT ColorCount FROM ColorsToSearch WHERE Color LIKE (?)',
        ('%hex defined color%',))
    suminitialhex = cur.fetchone()[0]
    print(str(suminitialhex)+' initially tagged as hexcolort1, while '
        +str(goodcount)+' were parsed')

    # Prevent our general hex color tag from being plotted now that we
    # have (in theory) every hex code accounted for.  If there were
    # any that the parser failed to catch, this statement will leave
    # that remainder in the entry (i.e. badcount variable).
    cur.execute('UPDATE ColorsToSearch SET ColorCount = ColorCount - (?)      \
        WHERE Color LIKE (?)',(goodcount,'%hex defined color%',))

    sql.commit()

# Version of ParseColorHexCode() that focuses on <hexcolorT2>, the
# non-hashtagged hex codes.  While it's very likely that all of these
# tagged as <hexcolorT2> were in-fact intended as hex color codes,
# since the hexsearch() regex used to tag these messages simply looks
# for six characters in succession that are all 0-9 or A-F, it's
# (theoretically) possible that--
#
# (1) a six letter long color,
# (2) containing only the letters [ABCDEF],
# (3) not found in the ~1000 colors of rgb.csv, and
# (4) not consumed by any previous hexsearch function
#
# --would be wrongly parsed as a hex code in this function. However,
# the alternative of not parsing the non hashtagged codes would mean
# throwing away 40+ messages to account for maybe one or two.
def ParseColorHexCodeNOHT():
    print('Parsing hex values from messages (Type2, no #)...')
    cur.execute('SELECT created, subject, body, tag, idstr FROM messages      \
        WHERE tag LIKE (?) ORDER BY created DESC',('%<hexcolorT2>%',))
    ColorHexCodeTable = cur.fetchall()
    goodcount = 0
    customcount = 0
    for item in ColorHexCodeTable:
        ParsedHex = ''
        # Search subject[1] and body[2] for the regex pattern.
        RegexSearchObj = re.search(r'([a-f0-9]{6})',
            item[1]+' '+item[2], re.M|re.I)
        ParsedHex = RegexSearchObj.group(1).lower()
        # Add the hex we parsed as a secondary tag for that entry
        cur.execute('UPDATE messages SET tag = tag || (?)                     \
            WHERE created LIKE (?) AND idstr LIKE (?)',
            ('<'+ParsedHex+'>','%'+str(item[0])+'%','%'+str(item[4])+'%'))
        cur.execute('SELECT COUNT(*) FROM ColorsToSearch                      \
        WHERE LOWER(ColorHex) LIKE LOWER(?);',('%#'+ParsedHex+'%',))
        colorexistsbool = cur.fetchone()[0]
        if colorexistsbool == 0:
            # If this is a new custom hex, add a new entry into the
            # colorstosearch summary table.
            customcount += 1
            cur.execute('INSERT INTO ColorsToSearch                           \
                (Color, ColorHex, ColorCount) VALUES(?,?,?)',
                ('customhexT2-'+str(customcount)+'-'+ParsedHex,
                '#'+ParsedHex,1))
        else:
            # If this hex already exists as an entry in the table, add
            # 1 to that count.  This accounts for both colors that
            # line up exactly with rgb.csv and multiple submissions of
            # the same custom hex.
            cur.execute('UPDATE ColorsToSearch SET ColorCount = ColorCount + 1\
                WHERE LOWER(ColorHex) LIKE LOWER(?);',('%#'+ParsedHex+'%',))
        goodcount += 1
            
    cur.execute('SELECT ColorCount FROM ColorsToSearch WHERE Color LIKE (?)',
        ('%hex defined colorNO#%',))
    suminitialhex = cur.fetchone()[0]
    print(str(suminitialhex)+' initially tagged as hexcolort2, while '
        +str(goodcount)+' were parsed')
    cur.execute('UPDATE ColorsToSearch SET ColorCount = ColorCount - (?)      \
        WHERE Color LIKE (?)',(goodcount,'%hex defined colorNO#%',))
    sql.commit()

# This if statement is where the whole program starts.  The name check
# makes sure this program is running on its own and not called by
# something else as it isn't set up to handle that.
if __name__ == '__main__':
    # Manual switch for function tests.  Determines if this program
    # runs as normal or if the program instead loads a pre-analyzed db
    # to quickly test post-messagedatabase-analysis functions.  Useful
    # when the main function takes a few minutes to complete but
    # you're only bugtesting a later function.
    if 1 == 1:
        extrasearch = 1
        main()
        exportreportcsv()
        exportgdocscsv()
        splitrgb()
        
        # renderHSVchart Usage: 
        # 1) 8=Sat on Y, 9=Val on Y
        # 2) 1 = Include Non-RGB tags and Unknown, 0 = clean plot
        # 3) 1 = Add annotation labels, 0 = keep clean
        # 4) Transparency of each bubble, from 0 (clear) to 1 (opaque)
        # 5) 1 = Lines around bubbles on, 0 = offset
        # 6) 1 = SVG export, 0 = PNG export
        
        # Informative
        renderHSVchart(9,1,1,.7,1,0)
        renderHSVchart(8,1,1,.7,1,0)
        
        # Clean
        renderHSVchart(9,0,0,1,0,0)
        renderHSVchart(9,0,0,.5,0,0)
        renderHSVchart(9,0,0,.9,0,0)
        renderHSVchart(9,0,0,.9,1,0)
        renderHSVchart(8,0,0,1,0,0)
        renderHSVchart(8,0,0,.5,0,0)
        renderHSVchart(8,0,0,.9,0,0)
        renderHSVchart(8,0,0,.9,1,0)
        
        renderHSVchart(9,0,0,.85,1,0)
        
        #SVGs
        renderHSVchart(9,0,0,.9,0,1)
        renderHSVchart(9,0,0,.8,1,1)
        
        RenderPieChart(8)
    else:
        # Re-initialize the sql connection
        sql.commit()
        sql.close()
        os.remove(destdbpath)
        print('deleted '+destdbname)
        srcdbname = 'messagearchive-TEST.db' # already analyzed db
        srcdbpath = cwd + srcdbname
        destdbname = 'messagearchive-rendertest-'+timevar+'.db'
        destdbpath = xportdir + destdbname
        shutil.copy2(srcdbpath, destdbpath)
        sql = sqlite3.connect(destdbpath)
        sql.create_function('REGEXP', 2, regexp)
        cur = sql.cursor()
        print('reconnected sqlite as '+destdbname)
        

        
    sql.commit()
    sql.close()
    print('Database saved as ' + destdbname)
    print('All exports can be found in ' + xportdir)
    print('Done after '+str(int(round(time.time()-starttime)))+ ' seconds.')

# https://www.python.org/dev/peps/pep-0008/
# I tried my best to follow this