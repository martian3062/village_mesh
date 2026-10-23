"""Optional static reference figure; requires matplotlib, not used by bootstrap."""
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
import v2_layout as site


def main():
    fig,ax=plt.subplots(figsize=(9,9),dpi=150)
    fig.patch.set_facecolor('#f7f4ec');ax.set_facecolor('#f7f4ec')
    selected={x['building_id']:x for x in site.PILOT['frontages']}
    for b in site.BUILDINGS:
        x,y=b['center']
        if not -8000<x<14000 or not -15000<y<10000:continue
        color='#d6d0c4'
        if b['id'] in selected:color='#bc6944' if selected[b['id']]['interior'] else '#e4b35c'
        ax.add_patch(Polygon([(x/100,y/100) for x,y in b['points']],facecolor=color,edgecolor='#716a5d',linewidth=.4))
    for r in site.ROADS:
        ax.plot([p[0]/100 for p in r['points']],[p[1]/100 for p in r['points']],color='#a4a59b',lw=1,zorder=2)
    points=site.PILOT['centerline_cm']
    ax.plot([p[0]/100 for p in points],[p[1]/100 for p in points],color='#245b53',lw=2.8,zorder=3,label='240 m OSM pilot route')
    for i,c in enumerate(site.PILOT['cameras']):
        x,y,z=c['position_cm'];angle=math.radians(c['yaw_degrees'])
        ax.arrow(x/100,y/100,math.cos(angle)*7,math.sin(angle)*7,head_width=2,color='#254a72',length_includes_head=True,zorder=4)
        ax.annotate(str(i+1),(x/100,y/100),xytext=(-13,7),textcoords='offset points',fontsize=8,color='#173c64',fontweight='bold')
    ax.scatter([6],[20.8],marker='*',s=130,color='#9d3434',zorder=5,label='V1 / V2 start')
    handles,_=ax.get_legend_handles_labels()
    handles += [Patch(color='#e4b35c',label='Pilot frontage'),Patch(color='#bc6944',label='Representative interior')]
    ax.legend(handles=handles,loc='lower right',fontsize=8,framealpha=.95)
    ax.set_xlim(-65,125);ax.set_ylim(-135,90);ax.set_aspect('equal')
    ax.set_xlabel('East from reference origin (m)');ax.set_ylabel('North from reference origin (m)')
    ax.set_title('PANDORI NIJJARAN | V2 STREET PILOT\n16 footprints / 3 representative interiors / 8 fixed cameras',loc='left',fontsize=12,pad=15)
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.12)
    fig.text(.1,.035,'OSM contributors / Overture Maps / Microsoft / Google. Footprints are sourced; architecture and levels are inferred.\nOrigin: 31.4610594 N, 75.7240654 E. No surveyed dimensions or local photo review.',fontsize=7,color='#595b53')
    fig.subplots_adjust(bottom=.13,top=.9)
    fig.savefig(site.ROOT/'Docs/V2/pilot_map.png',facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__=='__main__':main()
