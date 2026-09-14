import os, subprocess, tempfile
from flask import Flask, render_template, request, jsonify
app=Flask(__name__)
MAX_CODE=50000
TIMEOUT=5

def run_cmd(cmd, stdin='', cwd=None):
    try:
        p=subprocess.run(cmd,input=stdin,text=True,capture_output=True,cwd=cwd,timeout=TIMEOUT,start_new_session=True)
        return {'output':p.stdout[-100000:],'error':p.stderr[-100000:],'exit_code':p.returncode}
    except subprocess.TimeoutExpired:
        return {'output':'','error':f'Execution timed out after {TIMEOUT} seconds.','exit_code':124}
    except Exception as e:
        return {'output':'','error':str(e),'exit_code':1}

@app.get('/')
def home(): return render_template('index.html')
@app.get('/health')
def health(): return jsonify(status='ok')

@app.post('/api/run')
def run():
    d=request.get_json(silent=True) or {}; lang=d.get('language'); code=d.get('code',''); stdin=d.get('stdin','')
    if not isinstance(code,str) or len(code)>MAX_CODE: return jsonify(output='',error='Invalid or oversized code.',exit_code=1),400
    if lang=='python': return jsonify(run_cmd(['python3','-I','-S','-c',code],stdin))
    if lang=='javascript': return jsonify(run_cmd(['node','--use-strict','-e',code],stdin))
    if lang=='sql':
        with tempfile.TemporaryDirectory() as td:
            db=os.path.join(td,'lab.db')
            return jsonify(run_cmd(['sqlite3','-header','-column',db],code))
    if lang=='c':
        with tempfile.TemporaryDirectory() as td:
            src=os.path.join(td,'main.c'); exe=os.path.join(td,'program')
            open(src,'w',encoding='utf-8').write(code)
            comp=run_cmd(['gcc','-std=c17','-O0','-Wall',src,'-o',exe])
            if comp['exit_code']!=0: return jsonify(comp)
            return jsonify(run_cmd([exe],stdin))
    return jsonify(output='',error='Unsupported language.',exit_code=1),400

@app.post('/api/check')
def check():
    out={}
    for n,c in {'python':['python3','--version'],'javascript':['node','--version'],'c':['gcc','--version'],'sql':['sqlite3','--version']}.items():
        try:
            p=subprocess.run(c,capture_output=True,text=True,timeout=3)
            out[n]=(p.stdout or p.stderr).splitlines()[0] if p.returncode==0 else 'Unavailable'
        except Exception: out[n]='Unavailable'
    return jsonify(out)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
