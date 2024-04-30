import csv
from utils import *
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

def load_fights(g):
    print("Loading fights")

    with open("../data/raw_total_fight_data.csv") as f:
        reader = csv.reader(f, delimiter=';')

        # Skip header row
        next(reader)

        for row in reader:
            #print(row)
            # Columns: R_fighter, B_fighter, R_KD, B_KD, R_SIG_STR.,B_SIG_STR.,
            #          R_SIG_STR_pct, B_SIG_STR_pct, R_TOTAL_STR., B_TOTAL_STR.,
            #          R_TD, B_TD, R_TD_pct, B_TD_pct, R_SUB_ATT, B_SUB_ATT,
            #          R_REV, B_REV, R_CTRL, B_CTRL, R_HEAD, B_HEAD, R_BODY,
            #          B_BODY, R_LEG, B_LEG, R_DISTANCE, B_DISTANCE, R_CLINCH,
            #          B_CLINCH, R_GROUND, B_GROUND, win_by, last_round,
            #          last_round_time, Format, Referee, date, location,
            #          Fight_type, Winner
            
            R_fighter       = row[0]
            B_fighter       = row[1]
            R_KD            = int(row[2])
            B_KD            = int(row[3])
            R_SIG_STR       = percentage_from_ratio(row[4])
            B_SIG_STR       = percentage_from_ratio(row[5])
            
            R_SIG_STR_pct = row[6]
            if '%' in R_SIG_STR_pct:
                R_SIG_STR_pct = percentage_to_float(R_SIG_STR_pct)
            
            B_SIG_STR_pct = row[7]
            if '%' in B_SIG_STR_pct:
                B_SIG_STR_pct = percentage_to_float(B_SIG_STR_pct)

            R_TOTAL_STR     = percentage_from_ratio(row[8])
            B_TOTAL_STR     = percentage_from_ratio(row[9])
            R_TD            = percentage_from_ratio(row[10])
            B_TD            = percentage_from_ratio(row[11])

            R_TD_pct = row[12]
            if '%' in R_TD_pct:
                R_TD_pct = percentage_to_float(R_TD_pct)
            else:
                R_TD_pct = 0

            B_TD_pct = row[13]
            if '%' in B_TD_pct:
                B_TD_pct = percentage_to_float(B_TD_pct)
            else:
                B_TD_pct = 0.0

            R_SUB_ATT       = int(row[14])
            B_SUB_ATT       = int(row[15])
            R_REV           = int(row[16])
            B_REV           = int(row[17])

            R_CTRL = row[18]
            if ':' in R_CTRL:
                R_CTRL = time_to_seconds(R_CTRL)

            B_CTRL = row[19]
            if ':' in B_CTRL:
                B_CTRL = time_to_seconds(B_CTRL)

            R_HEAD          = percentage_from_ratio(row[20])
            B_HEAD          = percentage_from_ratio(row[21])
            R_BODY          = percentage_from_ratio(row[22])
            B_BODY          = percentage_from_ratio(row[23])
            R_LEG           = percentage_from_ratio(row[24])
            B_LEG           = percentage_from_ratio(row[25])
            R_DISTANCE      = percentage_from_ratio(row[26])
            B_DISTANCE      = percentage_from_ratio(row[27])
            R_CLINCH        = percentage_from_ratio(row[28])
            B_CLINCH        = percentage_from_ratio(row[29])
            R_GROUND        = percentage_from_ratio(row[30])
            B_GROUND        = percentage_from_ratio(row[31])
            win_by          = row[32]
            last_round      = int(row[33])
            last_round_time = time_to_seconds(row[34])
            Format          = row[35]

            # might be empty
            referee         = row[36]

            date            = date_to_timestamp(row[37])
            location        = row[38]
            Fight_type      = row[39]
            
            # might be empty
            Winner          = row[40]

            # create referee
            q = "MERGE (:Referee {Name: $name})"
            g.query(q, {'name': referee})

            # create card
            q = "MERGE (c:Card {Date: $date, Location: $location})"
            g.query(q, {'date': date, 'location': location})

            # create fight
            q = """MATCH (c:Card {Date: $date, Location: $location})
                   MATCH (ref:Referee {Name: $referee})
                   MATCH (r:Fighter {Name:$R_fighter})
                   MATCH (b:Fighter {Name:$B_fighter})
                   CREATE (f:Fight)-[:PART_OF]->(c)
                   SET f = $fight
                   CREATE (f)-[:RED]->(r)
                   CREATE (f)-[:BLUE]->(b)
                   CREATE (ref)-[:REFEREED]->(f)
                   RETURN ID(f)
                """
            f_id = g.query(q, {'date': date, 'location': location,
                'referee': referee, 'R_fighter': R_fighter,
                'B_fighter': B_fighter, 'fight': {'Last_round': last_round,
                    'Last_round_time': last_round_time, 'Format': Format,
                    'Fight_type': Fight_type}
                }).result_set[0][0]
            
            # mark winner & loser
            winner = Winner
            loser = B_fighter if Winner == R_fighter else R_fighter
            q = """MATCH (f:Fight) WHERE ID(f) = $fight_id
                   MATCH (l:Fighter {Name:$loser})
                   MATCH (w:Fighter {Name:$winner})
                   CREATE (w)-[:WON]->(f), (l)-[:LOST]->(f)
                """
            g.query(q, {'fight_id': f_id, 'loser': loser, 'winner': winner})

def load_fighters(g):
    print("Loading fighters")
    
    # index fighter's name
    g.create_node_range_index("Fighter", "Name")

    fighters = [] # list of fighters attributes

    with open("../data/raw_fighter_details.csv") as f:
        reader = csv.reader(f)

        # Columns: fighter_name, Height, Weight, Reach, Stance, DOB, SLpM,
        #          Str_Acc, SApM, Str_Def, TD_Avg, TD_Acc, TD_Def, Sub_Avg

        # Skip header row
        next(reader)

        for row in reader:
            fighter_name = row[0]
            Height       = row[1]
            Weight       = row[2]
            Reach        = row[3]
            Stance       = row[4]
            DOB          = row[5]
            SLpM         = row[6]
            Str_Acc      = row[7]
            SApM         = row[8]
            Str_Def      = row[9]
            TD_Avg       = row[10]
            TD_Acc       = row[11]
            TD_Def       = row[12]
            Sub_Avg      = row[13]
            
            # None empty attributes
            attrs = {}
            
            attrs['Name'] = fighter_name
            
            if Height != "":
                attrs['Height'] = height_to_cm(Height)
            
            if Weight != "":
                Weight = int(Weight.replace(' lbs.', ''))
                attrs['Weight'] = Weight

            if Reach != "":
                attrs['Reach'] = reach_to_cm(Reach)

            if Stance != "":
                attrs['Stance'] = Stance

            if DOB != "":
                attrs['DOB'] = date_to_timestamp(DOB)

            # Significant Strikes Landed per Minute
            attrs['SLpM'] = float(SLpM)

            # Strike accuracy
            attrs['Str_Acc'] = percentage_to_float(Str_Acc)

            # Significant Strikes Absorbed per Minute.
            attrs['SApM'] = float(SApM)

            # strikes defended
            attrs['Str_Def'] = percentage_to_float(Str_Def)

            # Takedown average
            attrs['TD_Avg'] = float(TD_Avg)

            # Takedown accuracy
            attrs['TD_Acc'] = percentage_to_float(TD_Acc)

            # Takedown defense
            attrs['TD_Def'] = percentage_to_float(TD_Def)

            # Submission average
            attrs['Sub_Avg'] = float(Sub_Avg)

            fighters.append(attrs)
        
        # Load all fighters in one go.
        q = "UNWIND $fighters as fighter CREATE (f:Fighter) SET f = fighter"
        g.query(q, {'fighters': fighters})

def main():
    # Connect to FalkorDB
    db = FalkorDB(host='localhost', port=6379)
    g  = db.select_graph("UFC")

    # Clear previous graph
    if "UFC" in db.list_graphs():
        g.delete()

    load_fighters(g)
    load_fights(g)

    print("All done")

if __name__ == "__main__":
    main()
