# relion_optics_group_assigner
## 概要
* (step1) EPUで保存されたムービーファイルの名前からoptics groupを見出して、どの画像がどのoptics groupに属するかのテーブルを作成
* (step2) 任意のparticle.star (run_data.starなど) に対し、step1で作成したテーブルに従って、各単粒子の情報にoptics groupの情報を追記し、data_opticsブロックも追記し、新しいstarファイルとして保存
* (step3) 出力されたstarファイルをRELIONでインポートしてctf refineとかでお使いください

## RELIONバージョン情報
* 入力のstarファイルはv3.0にもv3.1にも対応
* 出力のstarファイルはv3.1

## 必要要件
* Python 2 or 3
* Pythonライブラリ
  * NumPy, Pandas, progressbar2

## インストール
### CentOS 7 / Python 2 の場合
#### EPELリポジトリの有効化
`sudo yum install epel-release`

#### pipのインストール
`sudo yum install python2-pip`

#### ライブラリのインストール
```pip install --user progressbar2 numpy==1.16.6 pandas==0.23.4```

#### relion_optics_group_assignerのダウンロード
* 適当な場所にcloneしてください。

`git clone https://github.com/kttn8769/relion_optics_group_assigner.git`

### Python 3 の場合
全部最新版で動くと思いますので試してみてください。

## ヘルプメッセージ
roga_find_optics_groups.py と roga_add_optics_groups_to_star.py という2つのスクリプトが入っています。

仮に~/Softwares/relion_optics_group_assigner にダウンロードしたとすると、

`python ~/Softwares/relion_optics_group_assigner/roga_find_optics_groups.py --help`

のように--helpを付けて実行することでヘルプメッセージを確認できます。

## 使い方例
### (Step1) 画像の名前とoptics groupの対応表を作成する
#### ファイルのリストアップ
roga_find_optics_groups.pyは、EPUで保存された画像ファイル名のうち Data_ に続く2つの数字が同じものを同じoptics groupとしてまとめます。

まず画像ファイルのリストを作ります。例えば Movies というディレクトリにある mrc ファイルが手持ちの画像データのすべてであれば、

```
ls Movies/*.mrc > filelist.txt
```

とすればいいです。ファイルリストに記録されたファイル名からディレクトリパス部分と拡張子を除いた文字列が、対応表(csv)のfilename列に記録されます。Step2では、この文字列が、starファイルに記録されている単粒子画像ファイル名内に含まれているか否かでoptics groupの対応をとります。例えばstarファイルの中では画像ファイル名が `FoilHole_23126168_Data_23126835_23126836_20190423_2008.mrcs`の型式である時に、対応表(csv)のfilenameが`FoilHole_23126168_Data_23126835_23126836_20190423_2008_Fractions`となっていたりすると、後者は前者に含まれていないため、文字列検索に引っかからず、optics groupの対応が取れなくてエラーが出ます。そうならないようなファイル名をリストアップするように注意ください。

また、Step2である単粒子画像のoptics groupを検索するとき、対応表の中に2つ以上のマッチが見つかると、これもエラーになります。拡張子やファイル名の末尾を変えたシンボリックリンクとかがリストアップされるとこういうことが起こり得るため、それも注意ください。

撮影条件が違うために、ファイル名からの判断だけに頼らず確実にoptics groupを分けたいファイル群がある場合は、それぞれでファイルリストを作ってください。

```
ls Movies_session1/*.mrc > filelist1.txt
ls Movies_session2/*.mrc > filelist2.txt
```

#### (optional) MTFファイルと画像ピクセルサイズを列挙したテキストファイルの作成
各ファイルリストの画像に対応するMTFファイルと画像ピクセルサイズ(Å/pixel)を記述したテキストファイルを用意します。MTFファイルが無い場合や、与えたくない場合は、このファイルは作成しなくてよいです。

仮にファイル名をmtf_info_file.txtとして、中身の例は例えば

```
mtf_falcon3EC_200kV.star    0.67
```

など。ファイルリストが2個以上あるときはその分だけ行を追加してください。

MTFファイルはRELIONプロジェクトディレクトリからアクセス可能なパスで記述してください。例えばプロジェクトディレクトリにMTFファイルを置いておき、上記のようにファイル名だけ書くなどすれば良いです。

各種検出器のMTFファイルは https://github.com/3dem/relion/tree/master/data 等にあります。

#### 対応表の作成
例えば以下の様にすると、対応表(csv形式)が保存されます。

```
python roga_find_optics_groups.py --infiles filelist1.txt filelist2.txt --mtf_info_file mtf_info_file.txt --outfile optics_group_table.csv
```

間違いがないか十分確認してください。


### (Step2) starファイルにoptics groupの情報を追加する
roga_add_optics_groups_to_star.pyを使います。

例えば Refine3D/job020/run_data.star にoptics groupの情報を追記したい場合、例えば以下の様にします。数万行とかあるとちょっと時間がかかります。

```
python roga_add_optics_groups_to_star.py --input_star Refine3D/job020/run_data.star --output_star refine3d_job020_data_with_optics.star --optics_group_csv optics_group_table.csv --save_csv
```

もし --input_star が v3.0 である場合、--image_size オプションにより、単粒子画像の画素数(Refine3D/job020の単粒子画像の画素数。256 x 256なら、256)も与えてください。 --input_star が v3.1 の場合は、data_optics ブロック(1レコードしかないことが前提)から読み取った値をすべての単粒子に適用します。

異なる画素数とかピクセルサイズでとったデータを混ぜこぜで使うことには対応していないので、必要であればissueを立ててください。

--save_csv を付けると、出力starファイル名に _optics.csv と _particles.csv が追加されたファイルも保存されます。これらはそれぞれ data_opticsブロックと data_particlesブロックのcsvファイルなので、意図しないことが起きていないか確認をしてください。


### (Step3) RELIONでインポートして使う
生成されたstarファイルをparticle starファイルとしてインポートして、CTF refinementなどでお使いください。




