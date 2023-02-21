document.addEventListener("DOMContentLoaded", function() {
  getAllGroups();
});

const apiKey = 'session["key"]';
const groups= [];
const getAllGroups = async (num) => {
    if(num === 1){
    }
    let page = num;

    await axios({
        method: 'get',
	url: `https://api.northpass.com/v2/groups?page=${page}`,
        headers: {
            'accept': '*/*',
            'x-api-key': apiKey,
            'content-type': 'application/json'
        }
    })
    .then(async (res) => {
        if (res.data.links.next != null) {
            page++;
            for (let i = 0; i < res.data.data.length; i++) {
		let groupName = res.data.data[i].attributes.name;
		selectInput  = '<option value='+ groupName +'>'+ groupName+'</option>';
		$('#groups').append(selectInput);
		groups.push(res.data.data[i].attributes.name);
	    }
            await getAllGroups(page);
        } else {
            for (let i = 0; i < res.data.data.length; i++) {
		groups.push(res.data.data[i].attributes.name);
	      }
	}
      })
    .catch(err => {
        console.log(err);
      })
}
