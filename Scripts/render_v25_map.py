"""Map of the inferred V2.5 extension; original geographic data retain attribution."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import pandori_layout as geo

ROOT=Path(__file__).resolve().parents[1]
def main():
    read=lambda p:json.loads((ROOT/p).read_text())
    nav=read('Assets/NPC/navigation.json');nodes={n['id']:n['position_cm'] for n in nav['nodes']}
    fig,ax=plt.subplots(figsize=(11,10),facecolor='#f7f4ec');ax.set_facecolor('#f7f4ec')
    for b in geo.BUILDINGS:ax.add_patch(Polygon([(x/100,y/100) for x,y in b['points']],facecolor='#d5d1c7',edgecolor='#908d83',linewidth=.5))
    for a,b in nav['edges']:
        x,y=nodes[a],nodes[b];ax.plot([x[0]/100,y[0]/100],[x[1]/100,y[1]/100],color='#315d58',lw=2)
    colors=['#b0a34c','#b99057','#806649','#6d8a4a']
    for i,feature in enumerate(read('Assets/Farms/parcels.geojson')['features']):
        p=feature['properties'];ring=p['polygon_cm'];ax.add_patch(Polygon([(x/100,y/100) for x,y in ring],facecolor=colors[i],edgecolor='#304234'))
        ax.text((ring[0][0]+525)/100,(ring[0][1]-750)/100,p['crop_type'].replace('_','\n'),ha='center',va='center',fontsize=8)
    for key in ('farm_gate','farm_south','farm_shelter','vehicle_stop'):
        x,y,_=nodes[key];ax.plot(x/100,y/100,'o',color='#b14f32',ms=5);ax.annotate(key.replace('_',' '),(x/100,y/100),xytext=(8,6),textcoords='offset points',fontsize=8)
    ax.set(xlim=(-30,85),ylim=(-110,45),xlabel='East from reference origin (m)',ylabel='North from reference origin (m)')
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_title('V2.5 / FOUR INFERRED DEMONSTRATION PLOTS\nMapped street + authored farm access graph',loc='left',pad=18)
    fig.text(.12,.025,'OSM / Overture / Microsoft / Google geographic sources.\nPlot boundaries, shelter, widths and uses are design inference; ownership is unknown.',fontsize=9)
    fig.savefig(ROOT/'Docs/V25/extension_map.png',dpi=140,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':main()
